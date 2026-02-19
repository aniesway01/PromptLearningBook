# ATOM_TYPE: Type B
"""
修復 DB 中 title='登入' 的紀錄：重新爬取正確的標題和 prompt
用法: python fix_login_records.py
"""
import sys
import io
import socket
import sqlite3
import logging
import time
import random
import re
import json
import requests
from pathlib import Path
from datetime import datetime
from bs4 import BeautifulSoup

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# ── 強制 IPv4 ──
_original_getaddrinfo = socket.getaddrinfo
def _ipv4_only_getaddrinfo(*args, **kwargs):
    responses = _original_getaddrinfo(*args, **kwargs)
    return [r for r in responses if r[0] == socket.AF_INET] or responses
socket.getaddrinfo = _ipv4_only_getaddrinfo

# ── 路徑 ──
PROJECT_DIR = Path(__file__).resolve().parent.parent
DB_PATH = PROJECT_DIR / "uniform_map.db"
LOG_PATH = PROJECT_DIR / "logs" / "fix_login_records.log"
(PROJECT_DIR / "logs").mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(LOG_PATH, encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
log = logging.getLogger("FixLoginRecords")

BASE_URL = "https://uniform.wingzero.tw"
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
]


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


def scrape_detail_fixed(session, url):
    """用修復後的邏輯爬取詳情頁"""
    soup = fetch(session, url)
    if not soup:
        return None

    photo_id = url.rstrip('/').split('/')[-1]

    # 標題：優先 .page-inside 內的 h1
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
            title = raw.split('|')[0].strip() if '|' in raw else raw
    if title == "Untitled" or title == "登入":
        og_title = soup.find('meta', property='og:title')
        if og_title:
            title = og_title.get('content', title)

    # 圖片 URL
    img_url = None
    og = soup.find('meta', property='og:image')
    if og:
        img_url = og.get('content')
    if not img_url:
        for img_tag in soup.find_all('img', src=True):
            src = img_tag['src']
            if 'flickr' in src or 'static.flickr' in src:
                img_url = src
                break

    # Prompt：優先 #promptContent，再 og:description
    prompt = ""
    prompt_elem = soup.find(id='promptContent')
    if prompt_elem:
        prompt = prompt_elem.get_text(strip=True)
    if not prompt:
        prompt_elem = soup.find(class_='prompt-content')
        if prompt_elem:
            prompt = prompt_elem.get_text(strip=True)
    if not prompt:
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
    }


def main():
    log.info("=" * 50)
    log.info("修復 prompt=title 的紀錄（從 og:description 取得真正的 prompt）")

    conn = sqlite3.connect(str(DB_PATH))
    conn.execute("PRAGMA journal_mode=WAL")

    rows = conn.execute(
        "SELECT id, url FROM images WHERE prompt = title AND prompt != '' AND prompt IS NOT NULL"
    ).fetchall()
    log.info(f"找到 {len(rows)} 筆 prompt=title 需要修復的紀錄")

    if not rows:
        log.info("沒有需要修復的紀錄")
        conn.close()
        return

    session = requests.Session()

    # 先測試 3 筆
    test_rows = rows[:3]
    log.info(f"先測試 {len(test_rows)} 筆...")

    for rid, url in test_rows:
        data = scrape_detail_fixed(session, url)
        if data:
            log.info(f"  ID {rid}: title='{data['title']}' prompt='{data['prompt'][:80]}...'")
        else:
            log.warning(f"  ID {rid}: 爬取失敗")

    # 確認測試通過後，開始批量修復
    log.info("測試通過，開始批量修復...")

    fixed = 0
    failed = 0
    still_login = 0

    for i, (rid, url) in enumerate(rows, 1):
        if i % 50 == 0:
            log.info(f"進度: {i}/{len(rows)} (修復 {fixed}, 失敗 {failed}, 仍為登入 {still_login})")

        data = scrape_detail_fixed(session, url)
        if not data:
            failed += 1
            continue

        # 只在拿到比 title 更好的 prompt 時才更新
        if data['prompt'] == data['title'] or not data['prompt']:
            still_login += 1
            continue

        conn.execute(
            "UPDATE images SET prompt = ? WHERE id = ?",
            (data['prompt'], rid)
        )
        fixed += 1

        if fixed % 50 == 0:
            conn.commit()
            log.info(f"已 commit {fixed} 筆")

    conn.commit()
    conn.close()

    log.info(f"\n=== 修復完成 ===")
    log.info(f"總計: {len(rows)} 筆")
    log.info(f"成功修復 (取得更好的 prompt): {fixed}")
    log.info(f"爬取失敗: {failed}")
    log.info(f"無更好的 prompt: {still_login}")


if __name__ == "__main__":
    main()
