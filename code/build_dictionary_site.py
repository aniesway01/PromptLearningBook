"""
What: 把 curated.json(301案例)+ uniform_map.db(遠端圖URL)合成一個自足單檔 HTML——
      「文生圖 Prompt 學習詞典 + 案例參考書」,呈現 prompt<->圖<->技法 三層關聯。
Why: UniformMap 原只爬圖+靜態站,缺學習價值。依 council-api MVP 裁決重做:案例書+技法詞典樹+詞彙表,
      技法可反查案例。圖用 db 的 Flickr image_url(免下載)。
When: 重爬/重評後跑,或直接跑(用現有 curated.json)。輸出 site/index.html 開瀏覽器即用。
How: 純 code merge(curated.json examples join db image_url by id)→ 嵌入 HTML 模板(vanilla JS,
      無 build step,evaluation/評分存 localStorage)。ASCII 輸出。
"""
import io
import json
import sqlite3
import sys
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
HERE = Path(__file__).resolve().parent
ROOT = HERE.parent  # Tool/UniformMap
CURATED = ROOT / "data" / "curated.json"
DB = ROOT / "uniform_map.db"
OUT_DIR = ROOT / "site"


def load_image_urls() -> dict:
    """從 db 取 {id(str): image_url}。圖用遠端 Flickr URL,免本地下載。"""
    urls = {}
    if not DB.exists():
        return urls
    try:
        con = sqlite3.connect(str(DB))
        for rid, iurl in con.execute("SELECT id, image_url FROM images"):
            if iurl:
                urls[str(rid)] = iurl
        con.close()
    except sqlite3.Error as e:
        print(f"[WARN] db 讀取失敗: {e}")
    return urls


def build_data() -> dict:
    raw = json.loads(CURATED.read_text(encoding="utf-8"))
    examples = raw.get("examples", [])
    img = load_image_urls()
    out = []
    tech_count, vocab_count = {}, {}
    for e in examples:
        rid = str(e.get("id"))
        techs = e.get("key_techniques") or []
        vocab = e.get("vocabulary_used") or []
        for t in techs:
            tech_count[t] = tech_count.get(t, 0) + 1
        for v in vocab:
            vocab_count[v] = vocab_count.get(v, 0) + 1
        out.append({
            "id": rid,
            "img": img.get(rid, ""),           # 遠端 URL;沒有就空(UI 顯示佔位)
            "prompt": e.get("prompt", ""),
            "ptype": e.get("prompt_type", ""),
            "chapter": e.get("chapter", ""),
            "title": e.get("title", ""),
            "commentary": e.get("commentary", ""),
            "techs": techs,
            "vocab": vocab,
            "score": e.get("score", 0),
        })
    return {
        "examples": out,
        "techniques": sorted(tech_count.items(), key=lambda kv: -kv[1]),
        "vocabulary": sorted(vocab_count.items(), key=lambda kv: -kv[1]),
        "meta": raw.get("metadata", {}),
    }


HTML = r"""<!DOCTYPE html>
<html lang="zh-TW"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>UniformMap — 文生圖 Prompt 學習詞典</title>
<style>
:root{--bg:#0f1115;--card:#191c23;--card2:#21252e;--fg:#e6e8ee;--mut:#9aa3b2;--ac:#7aa2ff;--pill:#2b3450;--hl:#ffd166;}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--fg);font:14px/1.6 -apple-system,"Segoe UI","Microsoft JhengHei",sans-serif}
a{color:var(--ac)}
header{position:sticky;top:0;z-index:9;background:#0f1115ee;backdrop-filter:blur(6px);border-bottom:1px solid #2a2f3a;padding:10px 16px;display:flex;gap:12px;align-items:center;flex-wrap:wrap}
header h1{font-size:16px;margin:0 12px 0 0}
#q{flex:1;min-width:180px;background:var(--card2);border:1px solid #333a47;color:var(--fg);padding:8px 12px;border-radius:8px}
.wrap{display:flex;align-items:flex-start}
aside{width:280px;flex:none;position:sticky;top:56px;height:calc(100vh - 56px);overflow:auto;border-right:1px solid #2a2f3a;padding:12px}
aside h3{font-size:13px;color:var(--mut);margin:14px 0 6px;text-transform:uppercase;letter-spacing:.04em}
.tech{display:flex;justify-content:space-between;padding:4px 8px;border-radius:6px;cursor:pointer}
.tech:hover{background:var(--card2)}.tech.on{background:var(--ac);color:#0b1020}
.tech .n{color:var(--mut)}.tech.on .n{color:#0b1020}
main{flex:1;padding:14px;min-width:0}
.bar{color:var(--mut);margin-bottom:10px;display:flex;gap:10px;flex-wrap:wrap;align-items:center}
.chip{background:var(--pill);padding:3px 9px;border-radius:999px;cursor:pointer;font-size:12px}
.chip.on{background:var(--ac);color:#0b1020}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(420px,1fr));gap:14px}
.card{background:var(--card);border:1px solid #262b35;border-radius:12px;overflow:hidden;display:flex;flex-direction:column}
.card .top{display:flex;gap:10px;padding:10px}
.thumb{width:150px;height:150px;flex:none;border-radius:8px;object-fit:cover;background:var(--card2)}
.noimg{width:150px;height:150px;flex:none;border-radius:8px;background:var(--card2);display:flex;align-items:center;justify-content:center;color:var(--mut);font-size:12px;text-align:center;padding:6px}
.meta{min-width:0}.meta .t{font-weight:600;margin-bottom:4px}
.badge{display:inline-block;background:var(--pill);color:var(--mut);padding:1px 7px;border-radius:6px;font-size:11px;margin:0 4px 4px 0}
.score{color:var(--hl)}
.pills{padding:0 10px 8px}
.pill{display:inline-block;background:var(--pill);color:#cdd6ea;padding:2px 9px;border-radius:999px;font-size:12px;margin:0 5px 5px 0;cursor:pointer}
.pill:hover{background:var(--ac);color:#0b1020}
.commentary{padding:0 10px 8px;color:var(--mut);font-size:13px}
details{border-top:1px solid #262b35}summary{padding:8px 10px;cursor:pointer;color:var(--ac);font-size:13px}
pre{margin:0;padding:10px;background:#0c0e12;color:#cfe;white-space:pre-wrap;word-break:break-word;max-height:300px;overflow:auto;font:12px/1.5 ui-monospace,Consolas,monospace}
mark{background:var(--hl);color:#231a00;border-radius:3px;padding:0 2px}
.rate{padding:8px 10px;display:flex;gap:6px;align-items:center;color:var(--mut)}
.star{cursor:pointer;font-size:16px;color:#444b59}.star.on{color:var(--hl)}
.copy{margin-left:auto;background:var(--pill);border:none;color:var(--fg);padding:4px 10px;border-radius:6px;cursor:pointer}
@media(max-width:780px){aside{display:none}.grid{grid-template-columns:1fr}.thumb,.noimg{width:110px;height:110px}}
</style></head><body>
<header>
  <h1>UniformMap <span style="color:var(--mut);font-weight:400">文生圖 Prompt 學習詞典</span></h1>
  <input id="q" placeholder="搜尋 prompt / 技法 / 標題 / 詞彙 ...">
  <span id="count" style="color:var(--mut)"></span>
</header>
<div class="wrap">
  <aside>
    <h3>篩選</h3>
    <div id="chapters"></div>
    <h3>技法詞典（點擊反查案例）</h3>
    <div id="techlist"></div>
  </aside>
  <main>
    <div class="bar" id="activebar"></div>
    <div class="grid" id="grid"></div>
  </main>
</div>
<script>
const DATA = __DATA__;
const EX = DATA.examples, TECH = DATA.techniques, CH = (DATA.meta.chapters)||{};
let activeTech=null, activeCh=null, query="";
const rates = JSON.parse(localStorage.getItem("um_rates")||"{}");

function esc(s){return (s||"").replace(/[&<>]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;'}[c]));}
function highlight(prompt, vocab){
  let h = esc(prompt);
  (vocab||[]).forEach(v=>{ if(v&&v.length>1){ const re=new RegExp("("+v.replace(/[.*+?^${}()|[\]\\]/g,"\\$&")+")","g"); h=h.replace(re,"<mark>$1</mark>"); }});
  return h;
}
function matches(e){
  if(activeTech && !(e.techs||[]).includes(activeTech)) return false;
  if(activeCh && String(e.chapter)!==String(activeCh)) return false;
  if(query){ const q=query.toLowerCase();
    const hay=(e.prompt+" "+e.title+" "+e.commentary+" "+(e.techs||[]).join(" ")+" "+(e.vocab||[]).join(" ")).toLowerCase();
    if(!hay.includes(q)) return false; }
  return true;
}
function setRate(id,n){ rates[id]=n; localStorage.setItem("um_rates",JSON.stringify(rates)); render(); }

function render(){
  const list = EX.filter(matches);
  document.getElementById("count").textContent = list.length+" / "+EX.length+" 案例";
  const ab=document.getElementById("activebar"); ab.innerHTML="";
  if(activeTech){ab.innerHTML+=`<span class="chip on" onclick="activeTech=null;render()">技法: ${esc(activeTech)} ✕</span>`;}
  if(activeCh){ab.innerHTML+=`<span class="chip on" onclick="activeCh=null;render()">章 ${activeCh} ✕</span>`;}
  if(!activeTech&&!activeCh&&!query) ab.innerHTML='<span style="color:var(--mut)">全部案例（點左側技法可反查；點卡片技法標籤可篩選）</span>';
  const g=document.getElementById("grid");
  g.innerHTML = list.map(e=>{
    const stars=[1,2,3,4,5].map(n=>`<span class="star ${(rates[e.id]||0)>=n?'on':''}" onclick="setRate('${e.id}',${n})">★</span>`).join("");
    const img = e.img? `<img class="thumb" loading="lazy" src="${e.img}" onerror="this.outerHTML='<div class=noimg>圖未載<br>(遠端)</div>'">` : `<div class="noimg">無圖<br>(待重爬)</div>`;
    const pills=(e.techs||[]).map(t=>`<span class="pill" onclick="activeTech='${t.replace(/'/g,"\\'")}';render();scrollTo(0,0)">${esc(t)}</span>`).join("");
    return `<div class="card">
      <div class="top">${img}
        <div class="meta">
          <div class="t">${esc(e.title)||"(無標題)"}</div>
          <span class="badge">${esc(e.ptype)}</span><span class="badge">章 ${e.chapter}</span><span class="badge score">★${e.score}</span>
          <div class="commentary">${esc(e.commentary)}</div>
        </div></div>
      <div class="pills">${pills}</div>
      <details><summary>展開 Prompt（技法詞彙高亮）</summary><pre>${highlight(e.prompt,e.vocab)}</pre></details>
      <div class="rate">我的評分 ${stars}<button class="copy" onclick='navigator.clipboard.writeText(${JSON.stringify(e.prompt)});this.textContent="已複製"'>複製 Prompt</button></div>
    </div>`;
  }).join("");
}
// 章節 chips
document.getElementById("chapters").innerHTML = Object.keys(CH).sort().map(c=>`<span class="chip" onclick="activeCh=(activeCh==='${c}'?null:'${c}');render()">章 ${c} (${CH[c]})</span>`).join(" ");
// 技法詞典(按出現次數)
document.getElementById("techlist").innerHTML = TECH.map(([t,n])=>`<div class="tech" onclick="activeTech=(activeTech===${JSON.stringify(t)}?null:${JSON.stringify(t)});render()"><span>${esc(t)}</span><span class="n">${n}</span></div>`).join("");
document.getElementById("q").addEventListener("input",e=>{query=e.target.value.trim();render();});
render();
</script></body></html>
"""


def main():
    data = build_data()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    html = HTML.replace("__DATA__", json.dumps(data, ensure_ascii=False))
    out = OUT_DIR / "index.html"
    out.write_text(html, encoding="utf-8")
    n_img = sum(1 for e in data["examples"] if e["img"])
    print(f"[OK] 案例 {len(data['examples'])} 筆 | 有遠端圖 {n_img} | 技法 {len(data['techniques'])} 種")
    print(f"[OK] 輸出: {out}")
    print(f"[OPEN] start {out}")


if __name__ == "__main__":
    main()
