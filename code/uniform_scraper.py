# ATOM_TYPE: Type B


import os
import sys
import time
import random
import re
import logging
import requests
from pathlib import Path
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from abc import ABC, abstractmethod

# Path setup
_current_dir = Path(__file__).resolve().parent
_root_dir = _current_dir.parent  # (原 little-tool 容器判斷已無意義,UniformMap 早獨立)
if str(_root_dir) not in sys.path:
    sys.path.append(str(_root_dir))

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# User Agents List for Rotation
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
]

class BaseScraper(ABC):
    def __init__(self, output_dir):
        self.base_url = "https://uniform.wingzero.tw"
        self.root_output_dir = Path(output_dir)
        self.session = requests.Session()
        self.data = []
        self.root_output_dir.mkdir(parents=True, exist_ok=True)
        self.logger = logging.getLogger(self.__class__.__name__)

    def _get_headers(self):
        return {
            'User-Agent': random.choice(USER_AGENTS),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7',
        }

    def _wait(self):
        time.sleep(random.uniform(1, 3))

    def get_soup(self, url, retries=3):
        for attempt in range(retries):
            try:
                self._wait()
                response = self.session.get(url, headers=self._get_headers(), timeout=30)
                response.raise_for_status()
                return BeautifulSoup(response.text, 'html.parser')
            except Exception as e:
                self.logger.warning(f"Attempt {attempt+1}/{retries} failed for {url}: {e}")
                if attempt == retries - 1:
                    self.logger.error(f"Max retries reached for {url}")
                    return None
                time.sleep(2 * (attempt + 1))
        return None

    def sanitize_filename(self, name):
        name = re.sub(r'[<>:"/\\|?*]', '_', name)
        return name.replace(' ', '_')[:100]

    def log_failed_url(self, url, reason):
        with open(self.root_output_dir / "failed_urls.txt", "a", encoding="utf-8") as f:
            f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} | {url} | {reason}\n")

    def _download_image(self, url, folder_name, filename_prefix=""):
        if not url:
            return None

        try:
            if not url.startswith('http'):
                url = urljoin(self.base_url, url)

            target_dir = self.root_output_dir / "downloads" / folder_name
            target_dir.mkdir(parents=True, exist_ok=True)

            ext = Path(url).suffix
            if not ext or ext.lower() not in ['.jpg', '.jpeg', '.png', '.webp', '.gif']:
                ext = '.jpg'

            safe_name = self.sanitize_filename(filename_prefix)
            if not safe_name:
                safe_name = url.split('/')[-1].split('.')[0]

            filename = f"{safe_name}{ext}"
            filepath = target_dir / filename

            if filepath.exists() and filepath.stat().st_size > 0:
                self.logger.info(f"Skipping existing file: {filename}")
                return filename

            max_retries = 3
            for attempt in range(max_retries):
                try:
                    self._wait()
                    response = self.session.get(url, headers=self._get_headers(), stream=True, timeout=30)
                    response.raise_for_status()

                    tmp_filepath = filepath.with_suffix(filepath.suffix + '.tmp')
                    with open(tmp_filepath, 'wb') as f:
                        for chunk in response.iter_content(chunk_size=8192):
                            f.write(chunk)

                    if tmp_filepath.stat().st_size == 0:
                        tmp_filepath.unlink()
                        raise ValueError("Downloaded file is empty")

                    tmp_filepath.rename(filepath)
                    self.logger.info(f"Downloaded: {filename}")
                    return filename

                except Exception as e:
                    self.logger.warning(f"Download attempt {attempt+1} failed for {url}: {e}")
                    if tmp_filepath.exists():
                        tmp_filepath.unlink()
                    if filepath.exists():
                        filepath.unlink()
                    if attempt == max_retries - 1:
                        raise

        except Exception as e:
            self.logger.error(f"Failed to download {url}: {e}")
            self.log_failed_url(url, str(e))
            return None

    def log_url(self, filename, title, url, type_):
        with open(self.root_output_dir / "url.md", "a", encoding="utf-8") as f:
            f.write(f"- `{filename}`: [{title}]({url}) - {type_}\n")

    @abstractmethod
    def run(self):
        pass

class PhotoScraper(BaseScraper):
    def __init__(self, output_dir, max_pages=5):
        super().__init__(output_dir)
        self.max_pages = max_pages
        self.markdown_file = self.root_output_dir / "uniform_prompts.md"

    def _collect_links(self):
        links = []
        for page in range(1, self.max_pages + 1):
            url = f"{self.base_url}/zh-TW/ai-photos?page={page}"
            self.logger.info(f"Scanning page {page}...")
            soup = self.get_soup(url)
            if not soup:
                break

            found = 0
            for a in soup.find_all('a', href=True):
                if '/ai-photo/' in a['href']:
                    full_url = urljoin(self.base_url, a['href'])
                    if full_url not in links:
                        links.append(full_url)
                        found += 1
            if found == 0:
                break
        return links

    def _scrape_detail(self, url):
        soup = self.get_soup(url)
        if not soup:
            return None

        photo_id = url.split('/')[-1]
        title = soup.find('h1').text.strip() if soup.find('h1') else "Untitled"
        img_url = self._extract_image_url(soup)
        prompt = self._get_prompt(soup, img_url, title)
        metadata = self._get_metadata(soup)

        return {
            'id': photo_id,
            'title': title,
            'url': url,
            'image_url': img_url,
            'prompt': prompt,
            'metadata': metadata
        }

    def _extract_image_url(self, soup):
        img_tag = soup.find('img', {'class': re.compile(r'.*photo.*|.*image.*', re.I)})
        if img_tag:
            for attr in ['data-src', 'data-original', 'data-lazy', 'src']:
                val = img_tag.get(attr)
                if val:
                    return val
        og = soup.find('meta', property='og:image')
        if og:
            return og['content']
        return None

    def _get_prompt(self, soup, img_url, title):
        prompt_elem = self._find_prompt_element(soup)
        if prompt_elem:
            return prompt_elem.text.strip()
        elif img_url and img_url.get('alt'):
            return self._validate_prompt_with_ai(img_url.get('alt'))
        elif title and title != "Untitled":
            return title
        else:
            return ""

    def _find_prompt_element(self, soup):
        prompt_elem = soup.find(['div', 'p', 'textarea', 'pre'], {'class': re.compile(r'prompt', re.I)})
        if not prompt_elem:
            headers = soup.find_all(['h2', 'h3', 'label'])
            for h in headers:
                if 'prompt' in h.text.lower() or '提示' in h.text:
                    nxt = h.find_next(['p', 'div', 'textarea', 'pre'])
                    if nxt:
                        return nxt
        return prompt_elem

    def _get_metadata(self, soup):
        metadata = {}
        model = soup.find(string=re.compile(r'Gemini|ChatGPT|Midjourney|Stable Diffusion', re.I))
        if model:
            metadata['model'] = model.strip()
        return metadata

    def _validate_prompt_with_ai(self, text):
        if not text or len(text) < 3:
            return ""

        try:
            import google.generativeai as genai

            api_key = os.getenv("GEMINI_API_KEY")  # (原 _core.common.get_api_key 已不存在,直接走 env fallback)

            if not api_key:
                self.logger.warning("No GEMINI_API_KEY found, skipping AI validation")
                return text

            genai.configure(api_key=api_key)
            model = genai.GenerativeModel('gemini-2.0-flash-lite')

            prompt = f"""判斷以下文字是否為「有效的 AI 圖片生成 Prompt」或「有意義的圖片描述」。

規則：
- 如果是雜訊（如「點擊放大」、「Image 1」、「Preview」等無意義文字），回答 NO
- 如果是有效描述（如服裝風格、場景、人物特徵），回答 YES
- 只回答 YES 或 NO，不要解釋

文字: "{text}"

回答:"""

            response = model.generate_content(prompt)
            answer = response.text.strip().upper()

            if "YES" in answer:
                return text
            else:
                self.logger.info(f"AI filtered noise: {text[:30]}...")
                return ""

        except Exception as e:
            self.logger.warning(f"AI validation failed: {e}, using original text")
            return text

    def _process_photos(self, links):
        total = len(links)
        for i, url in enumerate(links, 1):
            self.logger.info(f"Processing {i}/{total}: {url}")
            data = self._scrape_detail(url)
            if data:
                local_img = self._download_image(data['image_url'], "photos", f"{data['id']}_{data['title']}")
                data['local_image'] = local_img
                self.data.append(data)
                if local_img:
                    self.log_url(local_img, data['title'], data['url'], "Photo")

    def _generate_markdown(self):
        with open(self.markdown_file, 'w', encoding='utf-8') as f:
            for item in self.data:
                if item.get('local_image'):
                    f.write(f"![{item['title']}](downloads/photos/{item['local_image']})\n\n")
                p_text = item['prompt'] if item['prompt'] else item['title']
                f.write(f"> {p_text}\n\n")
                f.write(f"---\n\n")
        self.logger.info(f"Markdown generated: {self.markdown_file}")

    def run(self):
        self.logger.info(f"Starting Photo Scraper (Max Pages: {self.max_pages})")
        all_links = self._collect_links()
        self._process_photos(all_links)
        self._generate_markdown()

class PromptScraper(BaseScraper):
    def __init__(self, output_dir):
        super().__init__(output_dir)
        self.markdown_file = self.root_output_dir / "uniform_tutorials.md"

    def _get_categories(self):
        soup = self.get_soup(f"{self.base_url}/zh-TW/prompts")
        if not soup:
            return []

        links = set()
        for a in soup.find_all('a', href=True):
            href = a['href']
            if '/prompts/' in href and href.count('/') <= 6:
                full = urljoin(self.base_url, href)
                if full != f"{self.base_url}/zh-TW/prompts":
                    links.add(full)
        return list(links)

    def _get_tutorial_links(self, categories):
        links = []
        for category in categories:
            soup = self.get_soup(category)
            if not soup:
                continue
            for a in soup.find_all('a', href=True):
                if '/prompts/' in a['href'] and '/ai-photo/' not in a['href']:
                    full_url = urljoin(self.base_url, a['href'])
                    links.append(full_url)
        return links

    def _scrape_tutorial(self, url):
        soup = self.get_soup(url)
        if not soup:
            return None

        title = soup.find('h1').text.strip() if soup.find('h1') else "Untitled"
        examples = []

        for img_tag in soup.find_all('img', {'class': re.compile(r'.*prompt.*', re.I)}):
            img_url = self._extract_image_url(img_tag)
            if img_url:
                label = img_tag.get('alt') or img_tag.get('title') or img_tag.get('data-title')
                examples.append({
                    'image': img_url,
                    'label': self._validate_prompt_with_ai(label or "")
                })

        return {
            'title': title,
            'url': url,
            'examples': examples
        }

    def _process_tutorials(self, links):
        total = len(links)
        for i, url in enumerate(links, 1):
            self.logger.info(f"Processing {i}/{total}: {url}")
            data = self._scrape_tutorial(url)
            if data:
                for example in data['examples']:
                    local_img = self._download_image(example['image'], "tutorials", f"{data['title']}_{example['label']}")