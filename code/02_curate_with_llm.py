"""
02_curate_with_llm.py
調用 Gemini Flash API 對候選圖片進行分類 + 生成教學註解
輸入: data/candidates.json
輸出: data/curated.json

批次策略: 每次 5 個 prompt，間隔 4 秒 (15 RPM)
API Key 輪替: 從 APIkeyBase.md 讀取多個 Gemini key
3 樣本驗證: 先跑 3 個確認格式再批量
"""
import json
import re
import sys
import time
import logging
import argparse
from pathlib import Path
from collections import Counter

# ── 路徑 ──
BASE_DIR = Path(__file__).resolve().parent.parent
CANDIDATES_PATH = BASE_DIR / "data" / "candidates.json"
OUTPUT_PATH = BASE_DIR / "data" / "curated.json"
API_KEY_PATH = Path("C:/AntiGravityFile/Docs/Standards/Credentials/APIkeyBase.md")

LOG_DIR = BASE_DIR / "logs"
LOG_DIR.mkdir(exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_DIR / "curate_with_llm.log", encoding="utf-8"),
        logging.StreamHandler(
            open(sys.stdout.fileno(), mode="w", encoding="utf-8", closefd=False)
        ),
    ],
)
log = logging.getLogger(__name__)

# ── 讀取 API Keys ──
def load_gemini_keys() -> list[str]:
    """從 APIkeyBase.md 讀取所有 Google Gemini API Keys"""
    if not API_KEY_PATH.exists():
        log.error(f"API Key 檔案不存在: {API_KEY_PATH}")
        sys.exit(1)

    content = API_KEY_PATH.read_text(encoding="utf-8")
    keys = []
    # 匹配 GOOGLE_API_KEY 或 GeminiFree 的值
    for match in re.finditer(r'\|\s*(?:GOOGLE_API_KEY\d+|GeminiFree\d+)\s*\|\s*`([^`]+)`', content):
        keys.append(match.group(1))

    log.info(f"載入 {len(keys)} 個 Gemini API Key")
    return keys


class GeminiKeyRotator:
    """API Key 輪替器"""
    def __init__(self, keys: list[str]):
        self.keys = keys
        self.index = 0
        self.error_counts = Counter()

    def get_key(self) -> str:
        key = self.keys[self.index]
        return key

    def rotate(self):
        self.index = (self.index + 1) % len(self.keys)

    def report_error(self, key: str):
        self.error_counts[key] += 1
        if self.error_counts[key] >= 3:
            log.warning(f"Key ...{key[-8:]} 已失敗 3 次，跳過")
        self.rotate()


# ── Gemini API 呼叫 ──
def call_gemini(prompt: str, api_key: str, model: str = "gemini-2.0-flash") -> dict | None:
    """呼叫 Gemini API，回傳 JSON"""
    import urllib.request
    import urllib.error

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.3,
            "responseMimeType": "application/json",
        },
    }

    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read().decode("utf-8"))
            text = result["candidates"][0]["content"]["parts"][0]["text"]
            return json.loads(text)
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        log.error(f"HTTP {e.code}: {body[:200]}")
        return None
    except Exception as e:
        log.error(f"API 呼叫失敗: {e}")
        return None


# ── 分類 + 註解 Prompt ──
CURATE_PROMPT_TEMPLATE = """你是 AI 繪圖教學專家。分析以下提示詞，判斷最適合的教學章節，並生成教學註解。

章節定義：
1. 人物主體 - 人數、年齡、族裔、體型、臉部、髮型、表情、視線、姿勢
2. 服裝 - 制服類型、上衣、下半身、腿部、鞋子、配飾、材質
3. 場景 - 室內外場景、背景、時段天氣
4. 光影 - 光源、方向、品質、光效
5. 鏡頭構圖 - 取景、角度、鏡頭參數、構圖法則
6. 風格 - 寫實、動漫、手繪、3D、美學風格
7. 色彩 - 基本色、色調、後製調色
8. 品質控制 - 正面品質詞、負面提示詞、平台語法
9. 特殊技法 - 身份鎖定、服裝鎖定、LoRA、ControlNet 等進階技術

請對以下每個提示詞回傳 JSON 陣列，每個元素包含：
- "id": 提示詞的 ID（原樣回傳）
- "chapter": 最適合的章節 ID (1-9 整數)
- "title": 一句話標題（繁體中文，10-20字）
- "commentary": 2-3 句教學點評（繁體中文），說明這個 prompt 展示了什麼技巧、為什麼有效
- "key_techniques": 2-3 個關鍵技巧名稱（繁體中文）
- "vocabulary_used": 從 prompt 中提取的 3-5 個重要辭典詞彙（英文原文）

只回傳 JSON 陣列，不要其他文字。

提示詞列表：
{prompts_block}
"""


def build_prompts_block(batch: list[dict]) -> str:
    """組裝批次 prompt 內容"""
    lines = []
    for item in batch:
        # 截斷過長的 prompt
        prompt_text = item["prompt"][:800]
        lines.append(f'[ID: {item["id"]}]\n{prompt_text}')
    return "\n\n---\n\n".join(lines)


def validate_result(result: list, batch: list[dict]) -> bool:
    """驗證 API 回傳格式"""
    if not isinstance(result, list):
        return False
    if len(result) != len(batch):
        log.warning(f"回傳數量不一致: 期望 {len(batch)}，得到 {len(result)}")
        return False
    required_fields = {"id", "chapter", "title", "commentary", "key_techniques", "vocabulary_used"}
    for item in result:
        if not isinstance(item, dict):
            return False
        if not required_fields.issubset(item.keys()):
            missing = required_fields - set(item.keys())
            log.warning(f"缺少欄位: {missing}")
            return False
        if not isinstance(item["chapter"], int) or not 1 <= item["chapter"] <= 9:
            log.warning(f"chapter 不合法: {item.get('chapter')}")
            return False
    return True


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="只跑 3 樣本驗證")
    parser.add_argument("--batch-size", type=int, default=5, help="每批數量")
    parser.add_argument("--delay", type=float, default=4.0, help="批次間隔秒數")
    parser.add_argument("--resume", action="store_true", help="從上次中斷處繼續")
    args = parser.parse_args()

    log.info("=" * 60)
    log.info("開始 LLM 自動策展")

    # 讀取候選
    if not CANDIDATES_PATH.exists():
        log.error(f"候選檔案不存在: {CANDIDATES_PATH}")
        log.error("請先執行 01_select_candidates.py")
        sys.exit(1)

    with open(CANDIDATES_PATH, "r", encoding="utf-8") as f:
        candidates_data = json.load(f)

    candidates = candidates_data["candidates"]
    log.info(f"載入 {len(candidates)} 個候選")

    # 載入 API Keys
    keys = load_gemini_keys()
    if not keys:
        log.error("沒有可用的 Gemini API Key")
        sys.exit(1)
    rotator = GeminiKeyRotator(keys)

    # 檢查是否有已完成的結果（續傳）
    curated_results = []
    done_ids = set()
    if args.resume and OUTPUT_PATH.exists():
        with open(OUTPUT_PATH, "r", encoding="utf-8") as f:
            existing = json.load(f)
            curated_results = existing.get("examples", [])
            done_ids = {r["id"] for r in curated_results}
            log.info(f"續傳模式: 已有 {len(done_ids)} 個結果")

    # 過濾已完成
    remaining = [c for c in candidates if c["id"] not in done_ids]
    log.info(f"待處理: {len(remaining)} 個")

    # ── 3 樣本驗證 ──
    if not args.resume or not done_ids:
        log.info("=" * 40)
        log.info("🔍 3 樣本驗證")
        test_batch = remaining[:3]
        prompts_block = build_prompts_block(test_batch)
        full_prompt = CURATE_PROMPT_TEMPLATE.format(prompts_block=prompts_block)

        key = rotator.get_key()
        result = call_gemini(full_prompt, key)

        if result is None:
            log.error("3 樣本驗證失敗（API 呼叫失敗），終止")
            sys.exit(1)

        if not validate_result(result, test_batch):
            log.error(f"3 樣本驗證失敗（格式不符），終止")
            log.error(f"回傳內容: {json.dumps(result, ensure_ascii=False)[:500]}")
            sys.exit(1)

        log.info("✅ 3 樣本驗證通過")
        for item in result:
            log.info(f"  [{item['id']}] 第{item['chapter']}章: {item['title']}")

        if args.dry_run:
            log.info("Dry run 完成，不進行批量處理")
            # 輸出測試結果
            test_output = {"test_results": result, "validation": "passed"}
            with open(BASE_DIR / "data" / "curate_test.json", "w", encoding="utf-8") as f:
                json.dump(test_output, f, ensure_ascii=False, indent=2)
            return

        # 把驗證結果加入
        for item in result:
            candidate = next((c for c in candidates if c["id"] == item["id"]), None)
            if candidate:
                curated_results.append(_merge_result(candidate, item))
                done_ids.add(item["id"])

        rotator.rotate()
        time.sleep(args.delay)

    # ── 批量處理 ──
    remaining = [c for c in candidates if c["id"] not in done_ids]
    total_batches = (len(remaining) + args.batch_size - 1) // args.batch_size
    log.info(f"批量處理: {len(remaining)} 個，{total_batches} 批")

    for i in range(0, len(remaining), args.batch_size):
        batch = remaining[i : i + args.batch_size]
        batch_num = i // args.batch_size + 1
        log.info(f"批次 {batch_num}/{total_batches} ({len(batch)} 個)")

        prompts_block = build_prompts_block(batch)
        full_prompt = CURATE_PROMPT_TEMPLATE.format(prompts_block=prompts_block)

        # 重試最多 3 次
        success = False
        for attempt in range(3):
            key = rotator.get_key()
            result = call_gemini(full_prompt, key)

            if result and validate_result(result, batch):
                for item in result:
                    candidate = next((c for c in candidates if c["id"] == item["id"]), None)
                    if candidate:
                        curated_results.append(_merge_result(candidate, item))
                        done_ids.add(item["id"])
                success = True
                break
            else:
                log.warning(f"  批次 {batch_num} 第 {attempt+1} 次失敗，切換 key 重試")
                rotator.report_error(key)
                time.sleep(2)

        if not success:
            log.error(f"  批次 {batch_num} 最終失敗，跳過 {len(batch)} 個")
            # 用預設值填充
            for c in batch:
                curated_results.append(_fallback_result(c))
                done_ids.add(c["id"])

        # 每 10 批存檔一次
        if batch_num % 10 == 0:
            _save_output(curated_results, candidates_data)
            log.info(f"  中途存檔: {len(curated_results)} 個")

        # 間隔
        if i + args.batch_size < len(remaining):
            time.sleep(args.delay)
            rotator.rotate()

    # ── 最終存檔 ──
    _save_output(curated_results, candidates_data)
    log.info(f"策展完成: {len(curated_results)} 個範例")

    # 統計
    chapter_counts = Counter(r["chapter"] for r in curated_results)
    for ch in range(1, 10):
        log.info(f"  第{ch}章: {chapter_counts.get(ch, 0)} 個")


def _merge_result(candidate: dict, llm_result: dict) -> dict:
    """合併候選資料與 LLM 結果"""
    return {
        "id": candidate["id"],
        "image": f"images/{candidate['id']}{candidate.get('local_ext', '.jpg')}",
        "prompt": candidate["prompt"],
        "prompt_type": candidate.get("prompt_type", "unknown"),
        "chapter": llm_result["chapter"],
        "title": llm_result["title"],
        "commentary": llm_result["commentary"],
        "key_techniques": llm_result.get("key_techniques", []),
        "vocabulary_used": llm_result.get("vocabulary_used", []),
        "score": candidate.get("score"),
    }


def _fallback_result(candidate: dict) -> dict:
    """LLM 失敗時的預設值"""
    return {
        "id": candidate["id"],
        "image": f"images/{candidate['id']}{candidate.get('local_ext', '.jpg')}",
        "prompt": candidate["prompt"],
        "prompt_type": candidate.get("prompt_type", "unknown"),
        "chapter": candidate.get("guessed_chapter", 1),
        "title": candidate.get("title", "未分類範例"),
        "commentary": "此範例展示了 AI 繪圖提示詞的應用。",
        "key_techniques": [],
        "vocabulary_used": [],
        "score": candidate.get("score"),
    }


def _save_output(results: list, candidates_data: dict):
    """存檔"""
    chapter_counts = dict(Counter(r["chapter"] for r in results))
    output = {
        "examples": results,
        "metadata": {
            "total": len(results),
            "chapters": {str(ch): chapter_counts.get(ch, 0) for ch in range(1, 10)},
            "source": str(CANDIDATES_PATH),
            "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        },
    }
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
