"""
03_build_site.py
組裝 GitHub Pages 靜態網站
1. 壓縮圖片到 site/images/ (800px, 品質 80%)
2. 複製辭典 HTML + JSON
3. 生成 index.html (主頁)
4. 生成 book.html (學習書)

用法:
  python 03_build_site.py                    # 使用所有 curated.json 範例
  python 03_build_site.py --min-score 6      # 只使用 score >= 6 的範例
  python 03_build_site.py --exclude-unscored # 排除未評分的範例
"""
import json
import sys
import shutil
import logging
import argparse
from pathlib import Path

# ── 路徑 ──
BASE_DIR = Path(__file__).resolve().parent.parent
CURATED_PATH = BASE_DIR / "data" / "curated.json"
SITE_DIR = BASE_DIR / "site"
IMAGES_DIR = SITE_DIR / "images"
DATA_DIR = SITE_DIR / "data"
PHOTOS_DIR = BASE_DIR / "downloads" / "photos"
DICT_HTML = BASE_DIR / "Doc" / "PromptDictionaryV3_tree.html"
VOCAB_JSON = BASE_DIR / "Doc" / "prompt_vocabulary_tree.json"

LOG_DIR = BASE_DIR / "logs"
LOG_DIR.mkdir(exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_DIR / "build_site.log", encoding="utf-8"),
        logging.StreamHandler(
            open(sys.stdout.fileno(), mode="w", encoding="utf-8", closefd=False)
        ),
    ],
)
log = logging.getLogger(__name__)

# ── 圖片壓縮 ──
def compress_images(curated_data: dict):
    """壓縮精選圖片到 site/images/"""
    try:
        from PIL import Image
    except ImportError:
        log.error("需要 Pillow: pip install Pillow")
        sys.exit(1)

    IMAGES_DIR.mkdir(parents=True, exist_ok=True)
    examples = curated_data.get("examples", [])
    success = 0
    skipped = 0
    failed = 0

    for ex in examples:
        img_id = ex["id"]
        # 找本地圖片 (格式: {id}_{title}.ext)
        src = None
        for ext in [".jpg", ".jpeg", ".png", ".webp"]:
            matches = list(PHOTOS_DIR.glob(f"{img_id}_*{ext}"))
            if matches:
                src = matches[0]
                break
            plain = PHOTOS_DIR / f"{img_id}{ext}"
            if plain.exists():
                src = plain
                break

        if not src:
            log.warning(f"找不到圖片: {img_id}")
            failed += 1
            continue

        dst = IMAGES_DIR / f"{img_id}.jpg"
        if dst.exists():
            skipped += 1
            continue

        try:
            img = Image.open(src)
            # 轉 RGB
            if img.mode in ("RGBA", "P"):
                img = img.convert("RGB")
            # 縮放到 800px 寬
            if img.width > 800:
                ratio = 800 / img.width
                new_h = int(img.height * ratio)
                img = img.resize((800, new_h), Image.LANCZOS)
            img.save(dst, "JPEG", quality=80, optimize=True)
            success += 1
        except Exception as e:
            log.error(f"壓縮失敗 {img_id}: {e}")
            failed += 1

    log.info(f"圖片壓縮: {success} 成功, {skipped} 跳過, {failed} 失敗")


def copy_dictionary():
    """複製辭典檔案"""
    if DICT_HTML.exists():
        shutil.copy2(DICT_HTML, SITE_DIR / "dictionary.html")
        log.info(f"複製辭典 HTML: {DICT_HTML.name}")
    else:
        log.warning(f"辭典 HTML 不存在: {DICT_HTML}")

    if VOCAB_JSON.exists():
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        shutil.copy2(VOCAB_JSON, DATA_DIR / "vocabulary_tree.json")
        log.info(f"複製詞彙 JSON: {VOCAB_JSON.name}")
    else:
        log.warning(f"詞彙 JSON 不存在: {VOCAB_JSON}")


def copy_curated_json(curated_data: dict):
    """寫入（可能已過濾的）curated.json 到 site/data/"""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(DATA_DIR / "curated.json", "w", encoding="utf-8") as f:
        json.dump(curated_data, f, ensure_ascii=False, indent=2)
    log.info(f"寫入 curated.json（{len(curated_data.get('examples', []))} 個範例）")


def generate_index_html():
    """生成首頁"""
    html = """<!DOCTYPE html>
<html lang="zh-TW">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Prompt 學習書</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
:root{--bg:#0f0f23;--bg2:#1a1a2e;--tx:#e8e8e8;--tx2:#a8a8a8;--ac:#4a90e2;--ac2:#e94b77}
body{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","Noto Sans TC",sans-serif;background:var(--bg);color:var(--tx);min-height:100vh;display:flex;flex-direction:column;align-items:center;justify-content:center;padding:40px 20px}
h1{font-size:2.5rem;margin-bottom:12px;background:linear-gradient(135deg,var(--ac),var(--ac2));-webkit-background-clip:text;-webkit-text-fill-color:transparent}
.subtitle{color:var(--tx2);font-size:1.1rem;margin-bottom:48px;text-align:center}
.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:24px;max-width:720px;width:100%}
.card{background:var(--bg2);border:1px solid rgba(255,255,255,.08);border-radius:16px;padding:32px;text-align:center;text-decoration:none;color:var(--tx);transition:all .3s}
.card:hover{transform:translateY(-4px);border-color:var(--ac);box-shadow:0 8px 32px rgba(74,144,226,.15)}
.card-icon{font-size:3rem;margin-bottom:16px}
.card h2{font-size:1.3rem;margin-bottom:8px}
.card p{color:var(--tx2);font-size:.9rem;line-height:1.6}
.footer{margin-top:48px;color:var(--tx2);font-size:.8rem;text-align:center}
.footer a{color:var(--ac);text-decoration:none}
</style>
</head>
<body>
<h1>Prompt 學習書</h1>
<p class="subtitle">AI 繪圖提示詞精選範例集 &amp; 詞彙辭典</p>
<div class="cards">
  <a class="card" href="book.html">
    <div class="card-icon">📖</div>
    <h2>學習書</h2>
    <p>~300 個精選範例，左圖右文排版<br>9 章分類 + 教學點評 + 關鍵技巧</p>
  </a>
  <a class="card" href="dictionary.html">
    <div class="card-icon">📚</div>
    <h2>詞彙辭典</h2>
    <p>樹狀結構提示詞辭典<br>搜尋、選詞、Prompt Builder</p>
  </a>
</div>
<div class="footer">
  <p>Powered by UniformMap Database</p>
</div>
</body>
</html>"""
    with open(SITE_DIR / "index.html", "w", encoding="utf-8") as f:
        f.write(html)
    log.info("生成 index.html")


def generate_book_html():
    """生成學習書 HTML"""
    html = r"""<!DOCTYPE html>
<html lang="zh-TW">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Prompt 學習書</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
:root{
  --bg:#0f0f23;--bg2:#1a1a2e;--bg3:#16213e;
  --tx:#e8e8e8;--tx2:#a8a8a8;--tx3:#6c6c8a;
  --ac:#4a90e2;--ac2:#e94b77;--ac3:#4ecdc4;--ac4:#f9ca24;
  --brd:rgba(255,255,255,.08);--shd:rgba(0,0,0,.3);
}
body.light{
  --bg:#f5f5f5;--bg2:#fff;--bg3:#e8edf2;
  --tx:#2c3e50;--tx2:#7f8c8d;--tx3:#b0b0b0;
  --brd:rgba(0,0,0,.08);--shd:rgba(0,0,0,.06);
}
body{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","Noto Sans TC",sans-serif;background:var(--bg);color:var(--tx);line-height:1.6}

/* Layout */
.app{display:flex;min-height:100vh}

/* Sidebar */
.sidebar{width:240px;background:var(--bg2);border-right:1px solid var(--brd);position:fixed;height:100vh;overflow-y:auto;z-index:100;transition:transform .3s}
.sidebar.hidden{transform:translateX(-100%)}
.sidebar-hdr{padding:16px;border-bottom:1px solid var(--brd)}
.sidebar-hdr h1{font-size:1rem;margin-bottom:4px}
.sidebar-hdr a{color:var(--ac);text-decoration:none;font-size:.8rem}
.nav-item{padding:10px 16px;cursor:pointer;border-left:3px solid transparent;font-size:.85rem;transition:all .2s;display:flex;justify-content:space-between;align-items:center}
.nav-item:hover{background:var(--bg3);border-left-color:var(--ac)}
.nav-item.active{background:var(--bg3);border-left-color:var(--ac);font-weight:600}
.nav-badge{font-size:.7rem;background:var(--ac);color:#fff;border-radius:10px;padding:1px 6px}
.nav-links{padding:12px 16px;border-top:1px solid var(--brd);display:flex;flex-direction:column;gap:8px}
.nav-links a{color:var(--tx2);text-decoration:none;font-size:.82rem;transition:color .2s}
.nav-links a:hover{color:var(--ac)}

/* Main */
.main{flex:1;margin-left:240px;display:flex;flex-direction:column;min-height:100vh}
.main.expanded{margin-left:0}

/* Toolbar */
.toolbar{padding:12px 24px;background:var(--bg2);border-bottom:1px solid var(--brd);display:flex;gap:8px;align-items:center;flex-wrap:wrap;position:sticky;top:0;z-index:50}
.toolbar input{flex:1;min-width:180px;padding:8px 12px;border:1px solid var(--brd);border-radius:6px;background:var(--bg);color:var(--tx);font-size:.85rem;outline:none}
.toolbar input:focus{border-color:var(--ac)}
.btn{padding:6px 12px;border:1px solid var(--brd);border-radius:6px;background:var(--bg2);color:var(--tx);cursor:pointer;font-size:.78rem;transition:all .2s;white-space:nowrap}
.btn:hover{background:var(--bg3);border-color:var(--ac)}
.toolbar select{padding:6px 10px;border:1px solid var(--brd);border-radius:6px;background:var(--bg);color:var(--tx);font-size:.82rem;outline:none;cursor:pointer}
.toolbar select:focus{border-color:var(--ac)}

/* Toggle sidebar (mobile) */
.toggle-sidebar{position:fixed;top:12px;left:12px;z-index:200;background:var(--bg2);border:1px solid var(--brd);border-radius:6px;padding:6px 10px;cursor:pointer;color:var(--tx);font-size:1rem;display:none}
@media(max-width:900px){.sidebar{transform:translateX(-100%)}.sidebar.show{transform:translateX(0)}.main{margin-left:0!important}.toggle-sidebar{display:block}}

/* Card */
.card-container{flex:1;padding:24px;display:flex;align-items:flex-start;justify-content:center}
.card{display:flex;gap:24px;max-width:960px;width:100%;background:var(--bg2);border:1px solid var(--brd);border-radius:12px;overflow:hidden;min-height:400px}
.card-img{flex:0 0 50%;max-width:50%;background:#000;display:flex;align-items:center;justify-content:center;overflow:hidden;position:relative}
.card-img img{width:100%;height:100%;object-fit:contain;max-height:80vh}
.card-img .no-img{color:var(--tx3);font-size:.9rem;padding:40px;text-align:center}
.card-body{flex:1;padding:24px;overflow-y:auto;max-height:80vh}
.card-body .chapter-tag{display:inline-block;padding:2px 10px;border-radius:12px;font-size:.72rem;font-weight:600;margin-bottom:12px;color:#fff}
.ch-1{background:#e94b77}.ch-2{background:#4a90e2}.ch-3{background:#4ecdc4}
.ch-4{background:#f9ca24;color:#333}.ch-5{background:#9b59b6}.ch-6{background:#e67e22}
.ch-7{background:#1abc9c}.ch-8{background:#3498db}.ch-9{background:#e74c3c}
.card-body h2{font-size:1.2rem;margin-bottom:16px;line-height:1.4}
.card-body .section{margin-bottom:16px}
.card-body .section-label{font-size:.75rem;color:var(--tx2);text-transform:uppercase;letter-spacing:.5px;margin-bottom:6px;font-weight:600}
.card-body .prompt-text{font-family:"Fira Code",monospace;font-size:.8rem;background:var(--bg);border:1px solid var(--brd);border-radius:6px;padding:12px;line-height:1.7;white-space:pre-wrap;word-break:break-all;max-height:200px;overflow-y:auto;color:var(--tx)}
.card-body .commentary{font-size:.88rem;line-height:1.8;color:var(--tx)}
.card-body .tags{display:flex;flex-wrap:wrap;gap:6px}
.card-body .tag{padding:3px 10px;border-radius:4px;font-size:.78rem;background:var(--bg3);border:1px solid var(--brd);color:var(--tx);cursor:pointer;transition:all .15s}
.card-body .tag:hover{border-color:var(--ac);color:var(--ac)}
.card-body .vocab-tag{background:rgba(74,144,226,.1);border-color:rgba(74,144,226,.3);color:var(--ac)}
.card-body .score-badge{display:inline-block;padding:2px 8px;border-radius:4px;font-size:.72rem;font-weight:600;margin-left:8px}
.score-high{background:rgba(46,204,113,.15);color:#2ecc71}
.score-mid{background:rgba(241,196,15,.15);color:#f1c40f}

/* Pagination */
.pagination{padding:16px 24px;background:var(--bg2);border-top:1px solid var(--brd);display:flex;align-items:center;justify-content:center;gap:16px}
.pagination .btn{min-width:100px;text-align:center}
.pagination .page-info{font-size:.85rem;color:var(--tx2);min-width:80px;text-align:center}

/* Chapter colors for nav */
.nav-ch-1{border-left-color:#e94b77!important}
.nav-ch-2{border-left-color:#4a90e2!important}
.nav-ch-3{border-left-color:#4ecdc4!important}
.nav-ch-4{border-left-color:#f9ca24!important}
.nav-ch-5{border-left-color:#9b59b6!important}
.nav-ch-6{border-left-color:#e67e22!important}
.nav-ch-7{border-left-color:#1abc9c!important}
.nav-ch-8{border-left-color:#3498db!important}
.nav-ch-9{border-left-color:#e74c3c!important}

/* Responsive */
@media(max-width:700px){
  .card{flex-direction:column}
  .card-img{flex:none;max-width:100%;max-height:50vh}
  .card-body{max-height:none}
}
</style>
</head>
<body>
<button class="toggle-sidebar" onclick="document.getElementById('sidebar').classList.toggle('show')">&#9776;</button>
<div class="app">
  <nav class="sidebar" id="sidebar">
    <div class="sidebar-hdr">
      <h1>Prompt 學習書</h1>
      <a href="index.html">&larr; 回首頁</a>
    </div>
    <div id="nav"></div>
    <div class="nav-links">
      <a href="dictionary.html">📚 詞彙辭典</a>
      <a href="index.html">🏠 首頁</a>
    </div>
  </nav>
  <div class="main" id="main">
    <div class="toolbar">
      <input type="text" id="search" placeholder="搜尋 prompt 內容..." oninput="onSearch(this.value)">
      <select id="minScore" onchange="onScoreFilter()">
        <option value="0">全部星級</option>
        <option value="5">★ 5+</option>
        <option value="6">★ 6+</option>
        <option value="7">★ 7+</option>
        <option value="8">★ 8+</option>
        <option value="9">★ 9+</option>
      </select>
      <button class="btn" id="themeBtn" onclick="toggleTheme()">☀️</button>
    </div>
    <div class="card-container" id="cardContainer">
      <div style="color:var(--tx2);text-align:center;padding:60px">載入中...</div>
    </div>
    <div class="pagination">
      <button class="btn" id="prevBtn" onclick="navigate(-1)">&larr; 上一個</button>
      <span class="page-info" id="pageInfo">-</span>
      <button class="btn" id="nextBtn" onclick="navigate(1)">下一個 &rarr;</button>
    </div>
  </div>
</div>

<script>
const CHAPTERS={1:"人物主體",2:"服裝",3:"場景",4:"光影",5:"鏡頭構圖",6:"風格",7:"色彩",8:"品質控制",9:"特殊技法"};
let DATA=null,filtered=[],currentIdx=0,currentChapter=0,minScoreFilter=0;

// Load data
fetch("data/curated.json")
  .then(r=>r.json())
  .then(d=>{DATA=d;init();})
  .catch(e=>{document.getElementById("cardContainer").innerHTML=`<div style="color:var(--ac2);padding:60px;text-align:center">載入失敗: ${e.message}<br><br>請確認 data/curated.json 存在</div>`;});

function init(){
  filtered=DATA.examples.slice();
  buildNav();
  renderCard();
}

function buildNav(){
  const nav=document.getElementById("nav");
  nav.innerHTML="";
  // 根據星級篩選計算基礎數據
  const baseData=minScoreFilter>0?DATA.examples.filter(e=>e.score&&e.score>=minScoreFilter):DATA.examples;
  // All
  const all=document.createElement("div");
  all.className="nav-item"+(currentChapter===0?" active":"");
  all.innerHTML=`<span>全部</span><span class="nav-badge">${baseData.length}</span>`;
  all.onclick=()=>switchChapter(0);
  nav.appendChild(all);
  // Chapters
  for(let ch=1;ch<=9;ch++){
    const count=baseData.filter(e=>e.chapter===ch).length;
    if(count===0)continue;
    const el=document.createElement("div");
    el.className=`nav-item nav-ch-${ch}`+(currentChapter===ch?" active":"");
    el.innerHTML=`<span>第${ch}章 ${CHAPTERS[ch]}</span><span class="nav-badge">${count}</span>`;
    el.onclick=(()=>{const c=ch;return()=>switchChapter(c);})();
    nav.appendChild(el);
  }
}

function switchChapter(ch){
  currentChapter=ch;
  currentIdx=0;
  applyFilter();
  buildNav();
  renderCard();
}

function applyFilter(){
  let result=DATA.examples;
  if(currentChapter>0)result=result.filter(e=>e.chapter===currentChapter);
  // 星級篩選
  if(minScoreFilter>0)result=result.filter(e=>e.score&&e.score>=minScoreFilter);
  const q=document.getElementById("search").value.trim().toLowerCase();
  if(q)result=result.filter(e=>(e.prompt||"").toLowerCase().includes(q)||(e.title||"").toLowerCase().includes(q)||(e.commentary||"").toLowerCase().includes(q));
  filtered=result;
  if(currentIdx>=filtered.length)currentIdx=Math.max(0,filtered.length-1);
}

function onScoreFilter(){
  minScoreFilter=parseInt(document.getElementById("minScore").value)||0;
  currentIdx=0;
  applyFilter();
  buildNav();
  renderCard();
}

function onSearch(q){
  currentIdx=0;
  applyFilter();
  renderCard();
}

function navigate(dir){
  currentIdx+=dir;
  if(currentIdx<0)currentIdx=filtered.length-1;
  if(currentIdx>=filtered.length)currentIdx=0;
  renderCard();
}

function renderCard(){
  const container=document.getElementById("cardContainer");
  const pageInfo=document.getElementById("pageInfo");

  if(!filtered.length){
    container.innerHTML='<div style="color:var(--tx2);padding:60px;text-align:center">沒有符合的範例</div>';
    pageInfo.textContent="0 / 0";
    return;
  }

  const ex=filtered[currentIdx];
  const ch=ex.chapter||1;
  const scoreBadge=ex.score?`<span class="score-badge ${ex.score>=9?'score-high':'score-mid'}">★ ${ex.score}</span>`:"";

  // Truncate prompt display
  const promptDisplay=ex.prompt||"(無提示詞)";

  container.innerHTML=`
<div class="card">
  <div class="card-img">
    <img src="${ex.image}" alt="${ex.title||''}" onerror="this.parentElement.innerHTML='<div class=no-img>圖片載入失敗<br>${ex.image}</div>'" loading="lazy">
  </div>
  <div class="card-body">
    <span class="chapter-tag ch-${ch}">第${ch}章 ${CHAPTERS[ch]||''}</span>${scoreBadge}
    <h2>${ex.title||'未命名'}</h2>

    <div class="section">
      <div class="section-label">提示詞</div>
      <div class="prompt-text">${escapeHtml(promptDisplay)}</div>
    </div>

    <div class="section">
      <div class="section-label">教學點評</div>
      <div class="commentary">${escapeHtml(ex.commentary||'')}</div>
    </div>

    ${ex.key_techniques&&ex.key_techniques.length?`
    <div class="section">
      <div class="section-label">關鍵技巧</div>
      <div class="tags">${ex.key_techniques.map(t=>`<span class="tag">${escapeHtml(t)}</span>`).join('')}</div>
    </div>`:''}

    ${ex.vocabulary_used&&ex.vocabulary_used.length?`
    <div class="section">
      <div class="section-label">相關詞彙</div>
      <div class="tags">${ex.vocabulary_used.map(v=>`<a class="tag vocab-tag" href="dictionary.html#${encodeURIComponent(v)}" target="_blank">${escapeHtml(v)}</a>`).join('')}</div>
    </div>`:''}

    <div class="section" style="margin-top:12px">
      <div style="font-size:.72rem;color:var(--tx3)">ID: ${ex.id} | 類型: ${ex.prompt_type||'—'}</div>
    </div>
  </div>
</div>`;

  pageInfo.textContent=`${currentIdx+1} / ${filtered.length}`;
}

function escapeHtml(s){
  const d=document.createElement('div');d.textContent=s;return d.innerHTML;
}

// Keyboard nav
document.addEventListener("keydown",e=>{
  if(e.target.tagName==="INPUT")return;
  if(e.key==="ArrowLeft"||e.key==="ArrowUp")navigate(-1);
  if(e.key==="ArrowRight"||e.key==="ArrowDown")navigate(1);
});

// Theme
function toggleTheme(){
  document.body.classList.toggle("light");
  const isLight=document.body.classList.contains("light");
  document.getElementById("themeBtn").textContent=isLight?"🌙":"☀️";
  localStorage.setItem("book-theme",isLight?"light":"dark");
}
if(localStorage.getItem("book-theme")==="light"){
  document.body.classList.add("light");
  document.getElementById("themeBtn").textContent="🌙";
}
</script>
</body>
</html>"""

    with open(SITE_DIR / "book.html", "w", encoding="utf-8") as f:
        f.write(html)
    log.info("生成 book.html")


def parse_args():
    parser = argparse.ArgumentParser(description="組裝學習書網站")
    parser.add_argument(
        "--min-score", type=float, default=None,
        help="只使用 score >= N 的範例（例如 --min-score 6）"
    )
    parser.add_argument(
        "--exclude-unscored", action="store_true",
        help="排除未評分的範例"
    )
    return parser.parse_args()


def filter_examples(examples: list, min_score: float = None, exclude_unscored: bool = False) -> list:
    """根據分數過濾範例"""
    if min_score is None and not exclude_unscored:
        return examples

    filtered = []
    for ex in examples:
        score = ex.get("score")
        # 排除未評分
        if exclude_unscored and score is None:
            continue
        # 分數門檻
        if min_score is not None and score is not None and score < min_score:
            continue
        # 如果有 min_score 但沒有 exclude_unscored，未評分的保留
        if min_score is not None and score is None and not exclude_unscored:
            filtered.append(ex)
            continue
        filtered.append(ex)
    return filtered


def main():
    args = parse_args()

    log.info("=" * 60)
    log.info("開始組裝網站")
    if args.min_score is not None:
        log.info(f"🎯 最低分數門檻: {args.min_score}")
    if args.exclude_unscored:
        log.info("🚫 排除未評分範例")

    # 建立目錄
    SITE_DIR.mkdir(parents=True, exist_ok=True)
    IMAGES_DIR.mkdir(parents=True, exist_ok=True)
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    # 讀取策展資料
    if not CURATED_PATH.exists():
        log.error(f"curated.json 不存在: {CURATED_PATH}")
        log.error("請先執行 02_curate_with_llm.py")
        sys.exit(1)

    with open(CURATED_PATH, "r", encoding="utf-8") as f:
        curated_data = json.load(f)

    original_count = len(curated_data.get('examples', []))
    log.info(f"載入 {original_count} 個範例")

    # 過濾範例
    curated_data['examples'] = filter_examples(
        curated_data.get('examples', []),
        min_score=args.min_score,
        exclude_unscored=args.exclude_unscored
    )
    filtered_count = len(curated_data['examples'])
    if filtered_count < original_count:
        log.info(f"📉 過濾後剩餘 {filtered_count} 個範例（移除 {original_count - filtered_count} 個）")

    # Step 1: 壓縮圖片
    log.info("Step 1: 壓縮圖片")
    compress_images(curated_data)

    # Step 2: 複製辭典
    log.info("Step 2: 複製辭典")
    copy_dictionary()

    # Step 3: 寫入 curated.json（過濾後版本）
    log.info("Step 3: 寫入 curated.json")
    copy_curated_json(curated_data)

    # Step 4: 生成 HTML
    log.info("Step 4: 生成 HTML")
    generate_index_html()
    generate_book_html()

    # ── 統計 ──
    total_size = sum(f.stat().st_size for f in SITE_DIR.rglob("*") if f.is_file())
    img_count = len(list(IMAGES_DIR.glob("*.jpg")))
    log.info(f"網站組裝完成:")
    log.info(f"  圖片: {img_count} 張")
    log.info(f"  總大小: {total_size / 1024 / 1024:.1f} MB")
    log.info(f"  路徑: {SITE_DIR}")

    # 檢查大小
    if total_size > 100 * 1024 * 1024:
        log.warning(f"⚠ 網站大小 {total_size/1024/1024:.0f} MB 超過 100 MB，建議進一步壓縮圖片")


if __name__ == "__main__":
    main()
