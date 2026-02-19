"""
01_select_candidates.py
從 uniform_map.db 篩選 ~300 張候選圖片
輸出: data/candidates.json

用法:
  python 01_select_candidates.py                    # 預設行為（包含未評分）
  python 01_select_candidates.py --min-score 6      # 只選 score >= 6 的圖片
  python 01_select_candidates.py --min-score 5 --exclude-unscored  # 排除未評分
"""
import sqlite3
import json
import re
import os
import sys
import logging
import argparse
from pathlib import Path
from collections import Counter

# ── 路徑設定 ──
BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "uniform_map.db"
OUTPUT_PATH = BASE_DIR / "data" / "candidates.json"
PHOTOS_DIR = BASE_DIR / "downloads" / "photos"

# ── 日誌 ──
LOG_DIR = BASE_DIR / "logs"
LOG_DIR.mkdir(exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_DIR / "select_candidates.log", encoding="utf-8"),
        logging.StreamHandler(
            open(sys.stdout.fileno(), mode="w", encoding="utf-8", closefd=False)
        ),
    ],
)
log = logging.getLogger(__name__)

# ── 章節關鍵字（簡易預分類）──
CHAPTER_KEYWORDS = {
    1: ["1girl", "solo", "1boy", "girl", "boy", "person", "woman", "man",
        "teen", "young", "student", "japanese", "korean", "face", "eyes",
        "smile", "looking", "gaze", "hair", "ponytail", "bangs"],
    2: ["uniform", "school uniform", "sailor", "blazer", "skirt", "blouse",
        "sweater", "dress", "outfit", "stockings", "socks", "shoes", "loafers",
        "heels", "ribbon", "tie", "cardigan", "vest", "jacket", "cosplay",
        "kimono", "maid", "gothic", "lolita"],
    3: ["classroom", "bedroom", "cafe", "office", "studio", "park", "street",
        "shrine", "rooftop", "station", "beach", "garden", "background",
        "indoor", "outdoor", "scene", "setting", "environment"],
    4: ["light", "lighting", "shadow", "sunlight", "daylight", "backlight",
        "rim light", "soft light", "dramatic", "golden hour", "neon",
        "window light", "studio lighting", "cinematic lighting"],
    5: ["portrait", "close-up", "full body", "upper body", "wide shot",
        "medium shot", "angle", "low angle", "high angle", "lens", "85mm",
        "50mm", "depth of field", "bokeh", "composition", "framing",
        "rule of thirds"],
    6: ["photorealistic", "anime", "illustration", "watercolor", "oil painting",
        "3d render", "miniature", "diorama", "pixel", "vintage", "retro",
        "cyberpunk", "realistic", "raw photo", "film"],
    7: ["color", "colour", "red", "blue", "pink", "gold", "navy", "warm tone",
        "cool tone", "pastel", "vibrant", "monochrome", "color grading",
        "palette", "desaturated", "saturation"],
    8: ["best quality", "masterpiece", "8k", "4k", "ultra detailed",
        "sharp focus", "high resolution", "negative prompt", "bad anatomy",
        "watermark", "blurry", "deformed", "--ar", "--v", "--niji"],
    9: ["identity_lock", "face_accuracy", "consistent character", "same face",
        "outfit_lock", "LoRA", "controlnet", "inpainting", "img2img",
        "reference image", "txt2img"],
}

# ── Prompt 類型偵測 ──
def detect_prompt_type(prompt: str) -> str:
    if not prompt:
        return "unknown"
    prompt = prompt.strip()
    # JSON 格式
    if prompt.startswith("{") or prompt.startswith("["):
        try:
            json.loads(prompt)
            return "json"
        except json.JSONDecodeError:
            pass
    # 短標籤（少於 50 字元且沒有逗號和句號）
    if len(prompt) < 50 and "," not in prompt and "." not in prompt:
        return "short_tag"
    # 逗號分隔標籤
    comma_count = prompt.count(",")
    word_count = len(prompt.split())
    if comma_count >= 3 and comma_count > word_count * 0.3:
        return "comma_tag"
    # 其餘視為自然語言
    return "natural"


def guess_chapter(prompt: str) -> int:
    """用關鍵字匹配猜測最適合的章節"""
    if not prompt:
        return 1
    prompt_lower = prompt.lower()
    scores = {}
    for ch, keywords in CHAPTER_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw.lower() in prompt_lower)
        if score > 0:
            scores[ch] = score
    if scores:
        return max(scores, key=scores.get)
    return 1  # 預設第 1 章


def check_local_image(image_id: str, title: str = "") -> tuple[str | None, str | None]:
    """檢查本地圖片是否存在，回傳 (副檔名, 完整檔名)
    圖片命名格式: {id}_{title}.ext
    """
    for ext in [".jpg", ".jpeg", ".png", ".webp"]:
        # 精確匹配: id_title.ext
        if title:
            exact = PHOTOS_DIR / f"{image_id}_{title}{ext}"
            if exact.exists():
                return ext, exact.name
        # 前綴匹配: id_*.ext
        matches = list(PHOTOS_DIR.glob(f"{image_id}_*{ext}"))
        if matches:
            return ext, matches[0].name
        # 純 id 匹配
        plain = PHOTOS_DIR / f"{image_id}{ext}"
        if plain.exists():
            return ext, plain.name
    return None, None


def parse_args():
    parser = argparse.ArgumentParser(description="篩選候選圖片")
    parser.add_argument(
        "--min-score", type=float, default=None,
        help="最低分數門檻（例如 --min-score 6 只選 score >= 6）"
    )
    parser.add_argument(
        "--exclude-unscored", action="store_true",
        help="排除未評分的圖片（預設會在 Tier 3 納入長 prompt 未評分圖片）"
    )
    return parser.parse_args()


def main():
    args = parse_args()

    log.info("=" * 60)
    log.info("開始篩選候選圖片")
    log.info(f"DB: {DB_PATH}")
    if args.min_score is not None:
        log.info(f"🎯 最低分數門檻: {args.min_score}")
    if args.exclude_unscored:
        log.info("🚫 排除未評分圖片")

    if not DB_PATH.exists():
        log.error(f"資料庫不存在: {DB_PATH}")
        sys.exit(1)

    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # ── 決定有效的分數門檻 ──
    min_score = args.min_score if args.min_score is not None else 0
    exclude_unscored = args.exclude_unscored

    # ── 第一層：score >= 9 全收（如果 min_score 允許）──
    if min_score <= 9:
        cur.execute("SELECT * FROM images WHERE score >= 9 AND prompt IS NOT NULL AND prompt != ''")
        tier1 = [dict(r) for r in cur.fetchall()]
    else:
        tier1 = []
    log.info(f"Tier 1 (score >= 9): {len(tier1)} 張")

    # ── 第二層：6 <= score < 9（如果 min_score 允許）──
    tier2_min = max(6, min_score)  # 取 6 和 min_score 的較大值
    if tier2_min < 9:
        cur.execute(f"SELECT * FROM images WHERE score >= {tier2_min} AND score < 9 AND prompt IS NOT NULL AND prompt != ''")
        tier2 = [dict(r) for r in cur.fetchall()]
    else:
        tier2 = []
    log.info(f"Tier 2 ({tier2_min} <= score < 9): {len(tier2)} 張")

    # ── 已收集的 ID ──
    collected_ids = {r["id"] for r in tier1} | {r["id"] for r in tier2}

    # ── 第三層：補齊到目標數量 ──
    # 根據 min_score 和 exclude_unscored 決定篩選條件
    if exclude_unscored:
        # 只選有評分且 score >= min_score 的
        tier3_sql = f"""
            SELECT * FROM images
            WHERE score IS NOT NULL AND score >= {min_score} AND score < {tier2_min}
              AND prompt IS NOT NULL AND prompt != ''
              AND length(prompt) >= 100
              AND image_url IS NOT NULL AND image_url != ''
        """
        log.info(f"Tier 3 條件: score >= {min_score} 且有評分")
    elif min_score > 0:
        # 選 score >= min_score 的（排除低分但保留未評分）
        tier3_sql = f"""
            SELECT * FROM images
            WHERE ((score IS NULL) OR (score >= {min_score} AND score < {tier2_min}))
              AND prompt IS NOT NULL AND prompt != ''
              AND length(prompt) >= 100
              AND image_url IS NOT NULL AND image_url != ''
        """
        log.info(f"Tier 3 條件: score >= {min_score} 或未評分")
    else:
        # 原始邏輯：包含未評分和低分
        tier3_sql = f"""
            SELECT * FROM images
            WHERE (score IS NULL OR score < {tier2_min})
              AND prompt IS NOT NULL AND prompt != ''
              AND length(prompt) >= 100
              AND image_url IS NOT NULL AND image_url != ''
        """
        log.info("Tier 3 條件: 未評分或低分（原始邏輯）")

    cur.execute(tier3_sql)
    tier3_pool = [dict(r) for r in cur.fetchall() if r["id"] not in collected_ids]
    log.info(f"Tier 3 候選池: {len(tier3_pool)} 張")

    # ── 按 prompt 類型分組 ──
    type_groups = {"short_tag": [], "comma_tag": [], "natural": [], "json": [], "unknown": []}
    for row in tier3_pool:
        pt = detect_prompt_type(row["prompt"])
        row["_prompt_type"] = pt
        type_groups.setdefault(pt, []).append(row)

    for pt, items in type_groups.items():
        log.info(f"  Tier 3 類型 {pt}: {len(items)} 張")

    # ── 計算還需要多少 ──
    target_total = 300
    still_need = target_total - len(tier1) - len(tier2)
    log.info(f"已收集 {len(tier1) + len(tier2)} 張，還需 {still_need} 張")

    # ── 按類型平衡抽取 ──
    tier3_selected = []
    if still_need > 0:
        # 按類型分配名額（自然語言 40%, JSON 25%, 逗號標籤 20%, 短標籤 15%）
        type_quotas = {
            "natural": int(still_need * 0.40),
            "json": int(still_need * 0.25),
            "comma_tag": int(still_need * 0.20),
            "short_tag": int(still_need * 0.15),
        }
        # 餘額給自然語言
        remainder = still_need - sum(type_quotas.values())
        type_quotas["natural"] += remainder

        for pt, quota in type_quotas.items():
            pool = type_groups.get(pt, [])
            # 按 prompt 長度排序（較長的 prompt 通常更有教學價值）
            pool.sort(key=lambda r: len(r.get("prompt", "")), reverse=True)
            selected = pool[:quota]
            tier3_selected.extend(selected)
            log.info(f"  從 {pt} 選取 {len(selected)}/{quota} 張")

    # ── 合併所有 ──
    all_candidates = tier1 + tier2 + tier3_selected

    # ── 檢查本地圖片存在性 ──
    final_candidates = []
    no_local = 0
    for row in all_candidates:
        ext, local_filename = check_local_image(row["id"], row.get("title", ""))
        if ext:
            row["local_ext"] = ext
            row["local_filename"] = local_filename
        else:
            no_local += 1
            # 仍然保留，屆時用 image_url
        # 偵測 prompt 類型
        if "_prompt_type" not in row:
            row["_prompt_type"] = detect_prompt_type(row["prompt"])
        # 預猜章節
        row["_guessed_chapter"] = guess_chapter(row["prompt"])
        final_candidates.append(row)

    log.info(f"最終候選: {len(final_candidates)} 張（{no_local} 張無本地圖片）")

    # ── 檢查各章節覆蓋 ──
    chapter_counts = Counter(r["_guessed_chapter"] for r in final_candidates)
    for ch in range(1, 10):
        count = chapter_counts.get(ch, 0)
        log.info(f"  第{ch}章預估: {count} 張")
        if count < 5:
            log.warning(f"  ⚠ 第{ch}章素材不足 ({count} < 5)")

    # ── Prompt 類型統計 ──
    type_counts = Counter(r["_prompt_type"] for r in final_candidates)
    for pt, cnt in type_counts.most_common():
        log.info(f"  類型 {pt}: {cnt} 張 ({cnt/len(final_candidates)*100:.1f}%)")

    # ── 輸出 JSON ──
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    output_data = {
        "candidates": [],
        "metadata": {
            "total": len(final_candidates),
            "tier1_count": len(tier1),
            "tier2_count": len(tier2),
            "tier3_count": len(tier3_selected),
            "prompt_types": dict(type_counts),
            "chapter_estimates": dict(chapter_counts),
            "filters": {
                "min_score": args.min_score,
                "exclude_unscored": args.exclude_unscored,
            },
        },
    }

    for row in final_candidates:
        output_data["candidates"].append({
            "id": row["id"],
            "title": row.get("title", ""),
            "prompt": row["prompt"],
            "prompt_type": row["_prompt_type"],
            "image_url": row.get("image_url", ""),
            "local_ext": row.get("local_ext"),
            "local_filename": row.get("local_filename"),
            "score": row.get("score"),
            "guessed_chapter": row["_guessed_chapter"],
        })

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)

    log.info(f"已輸出: {OUTPUT_PATH}")
    log.info(f"檔案大小: {OUTPUT_PATH.stat().st_size / 1024:.1f} KB")
    log.info("篩選完成")

    conn.close()


if __name__ == "__main__":
    main()
