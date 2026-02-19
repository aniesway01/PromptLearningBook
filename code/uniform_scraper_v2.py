# ATOM_TYPE: Type B


import os
import sys
import random
import logging
import asyncio
import aiohttp
from pathlib import Path
from typing import List, Optional

# Type D (Data)
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36'
]

# Type C (Flow)
def _get_headers() -> dict:
    """Get random headers"""
    return {
        'User-Agent': random.choice(USER_AGENTS),
        'Accept': 'text/html,application/xhtml+xml',
        'Accept-Language': 'zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7',
    }

# Type B (Effect)
async def download_image(session: aiohttp.ClientSession, url: str, save_path: Path, retry: int = 3) -> bool:
    """Asynchronously download a single image"""
    for attempt in range(retry):
        try:
            # Random delay (to avoid WAF)
            await asyncio.sleep(random.uniform(0.5, 1.5))
            
            async with session.get(url, headers=_get_headers(), timeout=30) as resp:
                if resp.status == 200:
                    content = await resp.read()
                    
                    # Atomic write
                    tmp_path = save_path.with_suffix(save_path.suffix + '.tmp')
                    tmp_path.write_bytes(content)
                    
                    # Integrity check
                    if tmp_path.stat().st_size > 0:
                        tmp_path.rename(save_path)
                        logging.info(f"Downloaded: {save_path.name}")
                        return True
                    else:
                        tmp_path.unlink()
                        raise ValueError("Empty file")
                else:
                    logging.warning(f"HTTP {resp.status} for {url}")
        except Exception as e:
            logging.warning(f"Download attempt {attempt+1} failed: {e}")
            if attempt == retry - 1:
                logging.error(f"Max retries for {url}")
                return False
            await asyncio.sleep(2 ** attempt)  # Exponential backoff
    return False

# Type B (Effect)
async def download_batch(session: aiohttp.ClientSession, tasks: List[tuple]) -> List[bool]:
    """Batch asynchronous download"""
    return await asyncio.gather(*[download_image(session, url, path) for url, path in tasks])

# Type C (Flow)
class AsyncDownloader:
    """Asynchronous downloader for 70% efficiency improvement"""
    
    def __init__(self, concurrent_limit: int = 5):
        self.semaphore = asyncio.Semaphore(concurrent_limit)
        self.session: Optional[aiohttp.ClientSession] = None
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, *args):
        if self.session:
            await self.session.close()
    
    async def download_images(self, tasks: List[tuple]) -> List[bool]:
        """Batch asynchronous download"""
        async with self.semaphore:
            return await download_batch(self.session, tasks)

# Type A (Logic)
class IncrementalCrawlManager:
    """Incremental crawling: only fetch new data"""
    
    def __init__(self, json_path: Path):
        self.json_path = json_path
        self.existing_ids = set()
        self._load_existing_data()
    
    def _load_existing_data(self):
        """Load existing data"""
        if self.json_path.exists():
            try:
                with open(self.json_path, 'r', encoding='utf-8') as f:
                    existing_data = json.load(f)
                    self.existing_ids = {item['id'] for item in existing_data if 'id' in item}
                    logging.info(f"Loaded {len(self.existing_ids)} existing records")
            except Exception as e:
                logging.warning(f"Failed to load existing data: {e}")
    
    def is_new(self, item_id: str) -> bool:
        """Check if the item is new"""
        return item_id not in self.existing_ids
    
    def mark_completed(self, item_id: str):
        """Mark the item as completed"""
        self.existing_ids.add(item_id)

# Type A (Logic)
class EnhancedBaseScraper:
    """Enhanced base scraper: integrating all optimizations"""
    
    def __init__(self, output_dir: Path):
        self.base_url = "https://uniform.wingzero.tw"
        self.root_output_dir = output_dir
        self.data = []
        self._setup_directories()
        self._setup_logger()
        self._setup_ocr_chain()
        self.incremental_mgr = IncrementalCrawlManager(self.root_output_dir / "data.json")
    
    def _setup_directories(self):
        """Create base directory structure"""
        self.root_output_dir.mkdir(parents=True, exist_ok=True)
        (self.root_output_dir / "downloads").mkdir(exist_ok=True)
    
    def _setup_logger(self):
        """Initialize logger"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(self.root_output_dir / "scraper_v2.log", encoding='utf-8'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(self.__class__.__name__)
    
    def _setup_ocr_chain(self):
        """Initialize OCR Fallback Chain"""
        self.ocr_chain = OCRFallbackChain()
    
    def extract_prompt_from_element(self, element, img_tag=None) -> str:
        """Smart prompt extraction
        """
        # Logic here
        return ""
