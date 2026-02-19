# ATOM_TYPE: Type B
"""
增量爬取 uniform.wingzero.tw 新圖片
強制 IPv4 繞過 Cloudflare IPv6 問題
用法: python incremental_scraper.py
"""
import socket
import re
import json
import time
import random
import logging
import sqlite3
import requests
from pathlib import Path
from datetime import datetime
from bs4 import BeautifulSoup
from urllib.parse import urljoin

# ── 強制 IPv4 ──
_original_getaddrinfo = socket.getaddrinfo
def _ipv4_only_getaddrinfo(*args, **kwargs):
    responses = _original_getaddrinfo(*args, **kwargs)
    return [r for r in responses if r[0] == socket.AF_INET] or responses
socket.getaddrinfo = _ipv4_only_getaddrinfo

# ── 路徑 ──
PROJECT_DIR = Path(__file__).resolve().parent.parent
DOWNLOADS_DIR = PROJECT_DIR / "downloads" / "photos"
DB_PATH = PROJECT_DIR / "uniform_map.db"
JSON_PATH = PROJECT_DIR / "ai_photos_data.json"
URL_LOG = PROJECT_DIR / "url.md"
LOG_PATH = PROJECT_DIR / "logs" / "incremental_scraper.log"

DOWNLOADS_DIR.mkdir(parents=True, exist_ok=True)
(PROJECT_DIR / "logs").mkdir(exist_ok=True)

# ── Logging ──
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(LOG_PATH, encoding='utf-8'),
        logging.StreamHandler()
    ]
)
log = logging.getLogger("IncrementalScraper")

BASE_URL = "https://uniform.wingzero.tw"
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
]


def get_session():
    s = requests.Session()
    return s


def get_headers():
    return {
        'User-Agent': random.choice(USER_AGENTS),
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'zh-TW,zh;q=0.9,en-US;q=0.8',
    }


def fetch(session, url, retries=3):
    for attempt in range(retries):
        try:
            time.sleep(random.uniform(1, 2.5))
            resp = session.get(url, headers=get_headers(), timeout=30)
            resp.raise_for_status()
            return BeautifulSoup(resp.text, 'html.parser')
        except Exception as e:
            log.warning(f"Attempt {attempt+1}/{retries} failed: {url} — {e}")
            if attempt < retries - 1:
                time.sleep(2 ** (attempt + 1))
    return None


def get_existing_ids():
    """從 SQLite 取得已有的 ID"""
    ids = set()
    if DB_PATH.exists():
        conn = sqlite3.connect(str(DB_PATH))
        for row in conn.execute("SELECT id FROM images"):
            ids.add(str(row[0]))
        conn.close()
    log.info(f"資料庫現有 {len(ids)} 筆")
    return ids


def collect_new_links(session, existing_ids, max_pages=110):
    """掃描列表頁，收集新圖片連結"""
    new_links = []
    consecutive_old = 0

    for page in range(1, max_pages + 1):
        url = f"{BASE_URL}/zh-TW/ai-photos?page={page}"
        log.info(f"掃描第 {page} 頁...")
        soup = fetch(session, url)
        if not soup:
            break

        found_new = 0
        for a in soup.find_all('a', href=True):
            href = a['href']
            if '/ai-photo/' in href and '/ai-photos' not in href:
                photo_id = href.rstrip('/').split('/')[-1]
                if photo_id.isdigit() and photo_id not in existing_ids:
                    full_url = urljoin(BASE_URL, href)
                    if full_url not in new_links:
                        new_links.append(full_url)
                        found_new += 1

        if found_new == 0:
            consecutive_old += 1
            if consecutive_old >= 3:
                log.info(f"連續 {consecutive_old} 頁無新圖，停止掃描")
                break
        else:
            consecutive_old = 0
            log.info(f"  第 {page} 頁發現 {found_new} 張新圖")

    log.info(f"共發現 {len(new_links)} 張新圖片")
    return new_links


def scrape_detail(session, url):
    """爬取單張圖片詳情頁"""
    soup = fetch(session, url)
    if not soup:
        return None

    photo_id = url.rstrip('/').split('/')[-1]

    # 標題：優先 .page-inside 內的 h1，其次 <title> 標籤，避免抓到導航列的「登入」
    title = "Untitled"
    page_inside = soup.find(class_='page-inside')
    if page_inside:
        h1 = page_inside.find('h1')
        if h1:
            title = h1.get_text(strip=True)
    if title == "Untitled" or title == "登入":
        title_tag = soup.find('title')
        if title_tag:
            raw = title_tag.get_text(strip=True)
            # 去掉 " | Uniform Map 制服地圖" 後綴
            title = raw.split('|')[0].strip() if '|' in raw else raw
    if title == "Untitled" or title == "登入":
        og_title = soup.find('meta', property='og:title')
        if og_title:
            title = og_title.get('content', title)

    # 圖片 URL：優先 og:image，再找頁面 img
    img_url = None
    og = soup.find('meta', property='og:image')
    if og:
        img_url = og.get('content')
    if not img_url:
        # 找 Flickr 圖片（主要圖片來源）
        for img_tag in soup.find_all('img', src=True):
            src = img_tag['src']
            if 'flickr' in src or 'static.flickr' in src:
                img_url = src
                break
    if not img_url:
        img_tag = soup.find('img', {'class': re.compile(r'photo|image|main', re.I)})
        if img_tag:
            for attr in ['data-src', 'data-original', 'data-lazy', 'src']:
                val = img_tag.get(attr)
                if val and val.startswith('http'):
                    img_url = val
                    break

    # Prompt：優先 #promptContent，再 og:description，最後 title
    prompt = ""
    prompt_elem = soup.find(id='promptContent')
    if prompt_elem:
        prompt = prompt_elem.get_text(strip=True)
    if not prompt:
        prompt_elem = soup.find(class_='prompt-content')
        if prompt_elem:
            prompt = prompt_elem.get_text(strip=True)
    if not prompt:
        # 很多頁面的 prompt 在 og:description 裡
        og_desc = soup.find('meta', property='og:description')
        if og_desc:
            prompt = og_desc.get('content', '').strip()
    if not prompt:
        meta_desc = soup.find('meta', {'name': 'description'})
        if meta_desc:
            prompt = meta_desc.get('content', '').strip()
    if not prompt:
        prompt = title

    return {
        'id': photo_id,
        'title': title,
        'url': url,
        'image_url': img_url,
        'prompt': prompt,
        'scraped_at': datetime.now().isoformat(),
    }


def download_image(session, url, photo_id, title):
    """下載圖片"""
    if not url:
        return None

    safe_title = re.sub(r'[<>:"/\\|?*]', '_', title)[:60]
    ext = Path(url).suffix.split('?')[0]
    if ext.lower() not in ['.jpg', '.jpeg', '.png', '.webp', '.gif']:
        ext = '.jpg'

    filename = f"{photo_id}_{safe_title}{ext}"
    filepath = DOWNLOADS_DIR / filename

    if filepath.exists() and filepath.stat().st_size > 1000:
        return filename

    for attempt in range(3):
        try:
            time.sleep(random.uniform(0.5, 1.5))
            resp = session.get(url, headers=get_headers(), stream=True, timeout=30)
            resp.raise_for_status()

            tmp = filepath.with_suffix(filepath.suffix + '.tmp')
            with open(tmp, 'wb') as f:
                for chunk in resp.iter_content(8192):
                    f.write(chunk)

            if tmp.stat().st_size > 500:
                tmp.rename(filepath)
                return filename
            else:
                tmp.unlink()
        except Exception as e:
            log.warning(f"圖片下載 attempt {attempt+1} 失敗: {e}")
            if attempt < 2:
                time.sleep(2 ** attempt)

    return None


def save_to_db(records):
    """寫入 SQLite"""
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.executemany(
        """INSERT OR REPLACE INTO images
           (id, title, url, image_url, local_image, prompt, scraped_at)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        [(r['id'], r['title'], r['url'], r['image_url'],
          r.get('local_image'), r['prompt'], r['scraped_at'])
         for r in records]
    )
    conn.commit()
    conn.close()


def append_to_json(records):
    """追加到 JSON"""
    existing = []
    if JSON_PATH.exists():
        try:
            existing = json.loads(JSON_PATH.read_text(encoding='utf-8'))
        except:
            pass

    existing_ids = {r['id'] for r in existing}
    new = [r for r in records if r['id'] not in existing_ids]
    existing.extend(new)

    JSON_PATH.write_text(
        json.dumps(existing, ensure_ascii=False, indent=2),
        encoding='utf-8'
    )
    log.info(f"JSON 追加 {len(new)} 筆，總計 {len(existing)} 筆")


def append_to_url_log(records):
    """追加到 url.md"""
    with open(URL_LOG, 'a', encoding='utf-8') as f:
        for r in records:
            if r.get('local_image'):
                f.write(f"- `{r['local_image']}`: [{r['title']}]({r['url']}) - Photo\n")


def main():
    log.info("=" * 50)
    log.info("增量爬取開始")

    session = get_session()

    # 連線測試
    try:
        resp = session.get(f"{BASE_URL}/zh-TW", headers=get_headers(), timeout=15)
        log.info(f"連線測試: HTTP {resp.status_code}")
    except Exception as e:
        log.error(f"連線失敗: {e}")
        return

    existing_ids = get_existing_ids()
    new_links = collect_new_links(session, existing_ids)

    if not new_links:
        log.info("沒有新圖片，結束")
        return

    # 爬取詳情 + 下載
    batch = []
    total = len(new_links)
    for i, link in enumerate(new_links, 1):
        log.info(f"[{i}/{total}] {link}")
        data = scrape_detail(session, link)
        if not data:
            continue

        local_img = download_image(session, data['image_url'], data['id'], data['title'])
        data['local_image'] = local_img
        batch.append(data)

        # 每 50 筆存一次
        if len(batch) >= 50:
            save_to_db(batch)
            append_to_json(batch)
            append_to_url_log(batch)
            log.info(f"已儲存 {i}/{total} 筆")
            batch = []

    # 儲存剩餘
    if batch:
        save_to_db(batch)
        append_to_json(batch)
        append_to_url_log(batch)

    log.info(f"完成！新增 {total} 張圖片")


if __name__ == "__main__":
    main()
