# Prompt 學習書 — 進度記錄

> 最後更新: 2026-02-01 20:32（由 Claude Opus 4.5 執行）

---

## 一句話現況

**Step 1~3 全部完成，網站已組裝好在 `site/`，尚未部署到 GitHub Pages。**

---

## 已完成的步驟

### Step 1: 篩選候選圖片 ✅

- 腳本: `code/01_select_candidates.py`
- 輸出: `data/candidates.json` (550 KB)
- 結果: **284 張候選**
  - Tier 1 (score >= 9): 85 張
  - Tier 2 (6 <= score < 9): 108 張
  - Tier 3 (未評分，prompt >= 100 字元): 91 張
- Prompt 類型分布: natural 135 / short_tag 95 / json 30 / comma_tag 24
- 284 張全部有本地圖片（`downloads/photos/` 中，命名格式 `{id}_{title}.ext`）

### Step 2: LLM 自動策展 ✅

- 腳本: `code/02_curate_with_llm.py`
- 輸出: `data/curated.json` (629 KB)
- 模型: Gemini 2.0 Flash (免費層)
- 結果: **284 個範例全部成功分類 + 生成教學註解**
- 章節分布:

| 章 | 主題 | 數量 |
|----|------|------|
| 1 | 人物主體 | 34 |
| 2 | 服裝 | 46 |
| 3 | 場景 | 99 |
| 4 | 光影 | 11 |
| 5 | 鏡頭構圖 | 15 |
| 6 | 風格 | 14 |
| 7 | 色彩 | 9 |
| 8 | 品質控制 | 5 |
| 9 | 特殊技法 | 51 |

- API 呼叫: 57 批 × 5 個 = 約 60 次請求，中間遇到 5 次 429 錯誤均自動切 key 重試成功
- 成本: $0

### Step 3: 組裝網站 ✅

- 腳本: `code/03_build_site.py`
- 圖片壓縮: 270/284 成功（14 張損壞檔案跳過，寬度 800px、品質 80%）
- 網站總大小: **34 MB**（遠低於 GitHub Pages 1GB 限制）

### 網站檔案結構

```
site/                          ← GitHub Pages 根目錄
├── index.html                 ← 首頁（兩張卡片：學習書 + 辭典）
├── book.html                  ← 學習書（左圖右文、章節導航、搜尋、鍵盤翻頁、暗/亮模式）
├── dictionary.html            ← V3 樹狀辭典（從 Doc/ 複製）
├── data/
│   ├── curated.json           ← 284 個範例的完整資料
│   └── vocabulary_tree.json   ← 詞彙樹
└── images/                    ← 270 張壓縮後的 JPG
    ├── 2321.jpg
    └── ...
```

---

## 尚未完成

### Step 4: 部署到 GitHub Pages ❌

執行以下命令即可：

```bash
cd C:\AntiGravityFile\Project\UniformMap
git init
git add site/ code/ data/ PROGRESS.md
git commit -m "Prompt Learning Book v1"
gh repo create PromptLearningBook --public --source=. --push
```

然後到 GitHub repo **Settings → Pages → Source** 設為 `main` branch, `/site` folder。

### 本地預覽方式

```bash
cd C:\AntiGravityFile\Project\UniformMap
python -m http.server 8000 --directory site
# 瀏覽器打開 http://localhost:8000
```

---

## 已知問題 & 改善空間

1. **14 張圖片損壞** — ID: 2237, 2052, 2045, 2075, 2063, 2123, 2067, 2119, 2234, 2118, 2095, 3228, 3488, 214。這些圖片在 book.html 中會顯示「圖片載入失敗」。可考慮從 curated.json 中移除或重新下載。

2. **章節分布不均** — 第 3 章（場景）有 99 個佔比過高，第 4/7/8 章偏少。LLM 分類偏向場景是因為大部分 prompt 都描述了場景。可考慮：
   - 手動調整部分範例的章節歸屬
   - 重新跑 02 腳本時調整 prompt 讓 LLM 更傾向分到其他章節

3. **辭典詞彙連結** — book.html 中的「相關詞彙」標籤連結到 `dictionary.html#詞彙名`，但辭典目前沒有處理 hash anchor 跳轉。需要在 dictionary.html 加入 hash 路由邏輯。

4. **響應式微調** — 手機版已支援（圖在上文在下），但未在實機測試過。

---

## 關鍵檔案索引

| 檔案 | 用途 |
|------|------|
| `code/01_select_candidates.py` | 從 DB 篩選候選圖片 |
| `code/02_curate_with_llm.py` | Gemini Flash 分類 + 註解（支援 `--dry-run`、`--resume`）|
| `code/03_build_site.py` | 壓縮圖片 + 複製辭典 + 生成 HTML |
| `data/candidates.json` | 篩選結果（284 筆）|
| `data/curated.json` | LLM 策展結果（284 筆）|
| `data/curate_test.json` | 3 樣本驗證結果 |
| `logs/*.log` | 每個腳本的執行日誌 |

## 重跑指南

如果需要重新執行某個步驟：

```bash
# 重新篩選（會覆蓋 candidates.json）
python code/01_select_candidates.py

# 重新策展（--resume 可從中斷處繼續）
python code/02_curate_with_llm.py
python code/02_curate_with_llm.py --resume   # 續跑

# 重新組裝網站（已壓縮的圖片會跳過）
python code/03_build_site.py
```
