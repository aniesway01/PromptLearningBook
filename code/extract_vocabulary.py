# ATOM_TYPE: Type B
"""
從 DB 的 prompt 中萃取提示詞詞彙，按辭典章節分類
用法: python extract_vocabulary.py
輸出: Doc/prompt_vocabulary_raw.json
"""
import sys
import io
import json
import re
import sqlite3
import logging
from pathlib import Path
from collections import Counter, defaultdict

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

PROJECT_DIR = Path(__file__).resolve().parent.parent
DB_PATH = PROJECT_DIR / "uniform_map.db"
OUT_PATH = PROJECT_DIR / "Doc" / "prompt_vocabulary_raw.json"
LOG_PATH = PROJECT_DIR / "logs" / "extract_vocabulary.log"

(PROJECT_DIR / "logs").mkdir(exist_ok=True)
(PROJECT_DIR / "Doc").mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(LOG_PATH, encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
log = logging.getLogger("VocabExtractor")

# ── 詞彙分類規則 ──
# 每個 category 對應辭典的一個章節/小節，用關鍵詞匹配
CATEGORIES = {
    "1.1_人物基本": [
        "girl", "girls", "boy", "woman", "man", "solo", "group", "couple",
        "young adult", "teen", "student", "japanese", "korean", "east asian",
        "slim", "petite", "athletic", "curvy", "slender", "tall",
    ],
    "1.2_臉部": [
        "face", "skin", "eyes", "eye", "nose", "lips", "lip", "mouth",
        "makeup", "eyeliner", "mascara", "blush", "glossy", "dewy",
        "flawless", "glass skin", "freckles", "mole", "dimple",
        "oval face", "v-line", "jawline", "cheek",
    ],
    "1.3_髮型": [
        "hair", "ponytail", "twin tail", "braid", "bun", "half-up",
        "bangs", "fringe", "straight hair", "wavy", "curly",
        "black hair", "brown hair", "blonde", "pink hair",
        "long hair", "short hair", "medium hair", "shoulder-length",
        "bob cut", "hime cut", "side tail",
    ],
    "1.4_表情": [
        "smile", "smiling", "grin", "laugh", "serious", "calm",
        "neutral", "cheerful", "playful", "wink", "blush",
        "open mouth", "closed mouth", "pout", "shy", "confident",
        "gentle", "innocent", "melancholy", "dreamy",
    ],
    "1.5_視線": [
        "looking at viewer", "looking at camera", "looking away",
        "looking down", "looking up", "looking to the side",
        "eye contact", "gaze", "staring", "glancing",
    ],
    "1.6_姿勢": [
        "standing", "sitting", "kneeling", "lying", "leaning",
        "walking", "running", "jumping", "crouching", "squatting",
        "hand on hip", "hands behind", "arms crossed", "hands clasped",
        "hand on head", "hand on chin", "resting", "holding",
        "legs crossed", "side-sitting", "weight shift",
        "turned", "profile", "from behind", "from side",
        "dynamic pose", "contrapposto", "elegant posture",
    ],
    "2.1_服裝類型": [
        "school uniform", "serafuku", "sailor", "blazer uniform",
        "casual", "streetwear", "formal", "cosplay", "lingerie",
        "maid", "nurse", "flight attendant", "office lady",
        "kimono", "yukata", "wedding dress", "military", "steampunk",
        "idol", "k-pop", "gothic", "lolita",
    ],
    "2.2_上半身": [
        "shirt", "blouse", "top", "sweater", "cardigan", "vest",
        "blazer", "jacket", "collar", "sailor collar", "tie", "ribbon",
        "bow", "necktie", "button", "sleeve", "cuff",
        "white shirt", "blue shirt", "crop top",
    ],
    "2.3_下半身": [
        "skirt", "pleated", "plaid", "miniskirt", "mini skirt",
        "shorts", "pants", "trousers", "jeans",
        "百褶", "格紋", "百褶裙",
    ],
    "2.4_腿部襪子": [
        "thighhigh", "knee-high", "over-the-knee", "pantyhose",
        "stockings", "tights", "socks", "ankle socks", "bare legs",
        "fishnet", "sheer", "opaque", "garter",
        "no-show", "crew socks", "絲襪", "過膝襪",
    ],
    "2.5_鞋子": [
        "loafer", "heel", "heels", "sneaker", "boot", "shoe",
        "sandal", "slipper", "platform", "mary jane",
        "leather shoes", "皮鞋",
    ],
    "2.6_配飾": [
        "earring", "necklace", "bracelet", "ring", "watch",
        "bag", "backpack", "hairpin", "hair clip", "headband",
        "glasses", "sunglasses", "choker", "hat", "cap", "beret",
        "scarf", "gloves", "umbrella",
    ],
    "3_場景環境": [
        "classroom", "school", "hallway", "library", "rooftop",
        "bedroom", "living room", "kitchen", "bathroom",
        "cafe", "coffee shop", "restaurant", "office",
        "studio", "white background", "backdrop",
        "street", "city", "urban", "park", "garden",
        "shrine", "temple", "church", "castle",
        "beach", "ocean", "mountain", "forest",
        "train station", "bridge", "staircase", "stairs",
        "window", "balcony", "corridor",
    ],
    "4_光影": [
        "natural light", "daylight", "sunlight", "backlighting",
        "rim light", "side light", "studio lighting", "ring light",
        "cinematic lighting", "dramatic lighting", "soft lighting",
        "warm light", "cool light", "golden hour", "blue hour",
        "shadow", "highlight", "contrast", "ambient",
        "bokeh", "lens flare", "glow", "bloom",
        "逆光", "柔光", "自然光",
    ],
    "5_鏡頭構圖": [
        "full body", "upper body", "cowboy shot", "portrait",
        "close-up", "extreme close-up", "wide shot",
        "eye level", "low angle", "high angle", "aerial",
        "85mm", "50mm", "35mm", "f/1.8", "f/2.8",
        "shallow depth", "depth of field", "bokeh",
        "centered", "rule of thirds", "symmetrical",
        "aspect ratio", "--ar",
    ],
    "6_風格渲染": [
        "photorealistic", "realistic", "raw photo", "hyper-realistic",
        "illustration", "anime", "cartoon", "manga",
        "sketch", "pencil", "watercolor", "oil painting",
        "3d render", "isometric", "miniature", "diorama",
        "film", "vintage", "retro", "noir",
        "pastel", "kawaii", "cyberpunk", "steampunk",
        "niji", "--v 6", "--v 5",
    ],
    "7_色彩": [
        "warm tone", "cool tone", "neutral", "pastel",
        "vibrant", "saturated", "desaturated", "monochrome",
        "color grading", "color palette",
        "navy", "white", "black", "red", "blue", "pink",
        "gold", "silver", "brown", "green", "purple",
    ],
    "8_品質控制": [
        "best quality", "masterpiece", "ultra detailed", "high-res",
        "high resolution", "4k", "8k", "hdr",
        "bad anatomy", "extra fingers", "watermark", "text",
        "blurry", "low quality", "deformed", "disfigured",
        "negative prompt",
    ],
    "9_特殊技法": [
        "identity_lock", "face_accuracy", "outfit_lock",
        "reference", "uploaded image", "maintain the exact",
        "do not alter", "consistency",
        "inpainting", "img2img", "controlnet",
        "lora", "checkpoint", "weight",
    ],
}


def load_prompts():
    """載入所有有效 prompt"""
    conn = sqlite3.connect(str(DB_PATH))
    rows = conn.execute(
        "SELECT id, title, prompt FROM images WHERE prompt IS NOT NULL AND prompt != '' AND prompt != title"
    ).fetchall()
    conn.close()
    log.info(f"載入 {len(rows)} 筆有效 prompt")
    return rows


def flatten_json_prompt(text):
    """把 JSON prompt 展平為文字"""
    try:
        data = json.loads(text)
        parts = []
        def walk(obj):
            if isinstance(obj, dict):
                for v in obj.values():
                    walk(v)
            elif isinstance(obj, list):
                for v in obj:
                    walk(v)
            elif isinstance(obj, str):
                parts.append(obj)
            elif isinstance(obj, (int, float, bool)):
                parts.append(str(obj))
        walk(data)
        return " ".join(parts)
    except (json.JSONDecodeError, TypeError):
        return text


def extract_terms(text):
    """從文字中提取有意義的片段"""
    text_lower = text.lower()
    found = defaultdict(list)

    for category, keywords in CATEGORIES.items():
        for kw in keywords:
            kw_lower = kw.lower()
            if kw_lower in text_lower:
                # 嘗試取得原文中的完整上下文
                idx = text_lower.find(kw_lower)
                if idx >= 0:
                    # 取原始大小寫
                    original = text[idx:idx+len(kw)]
                    found[category].append(original)

    return found


def extract_comma_tags(text):
    """從逗號分隔的 tag 風格 prompt 中提取"""
    # 移除 JSON
    if text.strip().startswith('{'):
        return []
    tags = [t.strip() for t in re.split(r'[,，、\n]', text) if t.strip()]
    return [t for t in tags if 2 <= len(t) <= 80]


def main():
    log.info("開始萃取提示詞詞彙")

    rows = load_prompts()
    if not rows:
        log.error("沒有可用的 prompt")
        return

    # 統計
    all_terms = defaultdict(Counter)  # category -> {term: count}
    all_tags = Counter()  # 所有 comma-separated tags
    prompt_types = Counter()

    for pid, title, prompt in rows:
        # 分類 prompt 類型
        if prompt.strip().startswith('{'):
            prompt_types['json'] += 1
            flat = flatten_json_prompt(prompt)
        else:
            flat = prompt
            if ',' in prompt and len(prompt) > 30:
                prompt_types['tags'] += 1
            else:
                prompt_types['natural'] += 1

        # 關鍵詞匹配
        terms = extract_terms(flat)
        for cat, words in terms.items():
            for w in words:
                all_terms[cat][w.lower()] += 1

        # Tag 提取
        tags = extract_comma_tags(flat)
        for t in tags:
            all_tags[t.lower()] += 1

    # 整理輸出
    result = {
        "metadata": {
            "total_prompts": len(rows),
            "prompt_types": dict(prompt_types),
        },
        "vocabulary_by_chapter": {},
        "top_tags": [],
        "uncategorized_tags": [],
    }

    # 每個章節的詞彙 (按頻率排序)
    for cat in sorted(all_terms.keys()):
        terms = all_terms[cat]
        result["vocabulary_by_chapter"][cat] = [
            {"term": term, "count": count}
            for term, count in terms.most_common(100)
        ]

    # 全局 top tags
    result["top_tags"] = [
        {"tag": tag, "count": count}
        for tag, count in all_tags.most_common(200)
    ]

    # 找出未被分類的高頻 tag
    categorized = set()
    for cat_keywords in CATEGORIES.values():
        for kw in cat_keywords:
            categorized.add(kw.lower())

    uncategorized = []
    for tag, count in all_tags.most_common(500):
        tag_lower = tag.lower()
        is_categorized = any(kw in tag_lower or tag_lower in kw for kw in categorized)
        if not is_categorized and count >= 3 and len(tag) > 3:
            uncategorized.append({"tag": tag, "count": count})

    result["uncategorized_tags"] = uncategorized[:100]

    # 寫入
    OUT_PATH.write_text(
        json.dumps(result, ensure_ascii=False, indent=2),
        encoding='utf-8'
    )
    log.info(f"詞彙萃取完成，輸出: {OUT_PATH}")

    # 摘要
    log.info(f"\n=== 摘要 ===")
    log.info(f"Prompt 類型: {dict(prompt_types)}")
    for cat in sorted(all_terms.keys()):
        top3 = all_terms[cat].most_common(3)
        top3_str = ", ".join(f"{t}({c})" for t, c in top3)
        log.info(f"  {cat}: {len(all_terms[cat])} 詞 — {top3_str}")
    log.info(f"未分類高頻 tag: {len(uncategorized)} 個")


if __name__ == "__main__":
    main()
