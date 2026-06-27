# UniformMap — Claude Design Brief（貼進 claude.ai/design 用）

> 用法:把下面「## 設計 Prompt」整段貼進 Claude Design(claude.ai/design)→ 跑出 UI →
> 匯出 HTML 或「交接給 Claude Code」→ 回到這裡讓我接真實資料(`data/curated.json`)實作。
> 此 brief 整合了 council-api 議會 MVP 裁決 + 真實資料 schema(非憑空)。

## 產品一句話
一個「**學習文生圖的 prompt 詞典 + 別人實際案例的參考書**」——清楚呈現 **prompt ↔ 生成圖 ↔ 可複用技法** 的三層對應,讓使用者從別人的成功案例反推可複用的提示詞技法。

## 真實資料結構（每筆,來自 data/curated.json）
```
id           : 唯一碼
image        : 圖片相對路徑 (images/{id}.jpg)
prompt       : 完整 prompt 原文
prompt_type  : json | natural | comma_tag | short_tag (提示詞風格)
chapter      : 1-9 (教學章節分類)
title        : 教學標題
commentary   : LLM 生成的教學說明
key_techniques : 技法標籤清單 (風格/構圖/光線/材質...)
vocabulary_used: 詞彙標籤清單
score        : 品質分 0-10
```

## 設計 Prompt（貼這段進 Claude Design）
---
設計一個學習型 web app,主題是「文生圖 Prompt 學習詞典 + 案例參考書」。核心價值是讓使用者看懂
「**prompt 文字 ↔ 生成圖片 ↔ 可複用技法**」三層關係。深色主題,響應式(桌面/手機)。

**三個主視圖:**
1. **案例書(Case Book)** — 主畫面。左圖右文卡片流:左邊大圖(生成結果),右邊該圖的完整 prompt
   原文 + 教學說明(commentary)。prompt 文字中命中的「技法標籤」用高亮色標出,滑鼠移上去顯示該
   技法解釋。每張卡片頂部有 prompt_type 徽章(json/natural/comma_tag/short_tag)與章節標籤。
2. **技法詞典(Technique Dictionary)** — 側邊可收合樹狀導覽。按「技法類別(風格/構圖/光線/材質...)」
   分層列出所有技法標籤;點一個技法 → 右側案例書篩出所有用到該技法的圖文卡片。這是「反查」入口:
   想學某技法 → 看誰用了它 → 看它配什麼 prompt 配什麼圖。
3. **詞彙表(Vocabulary)** — 收錄 prompt 裡高頻可複用詞彙,點詞 → 跳到用該詞的案例。

**互動:**
- 頂部搜尋框:可搜 prompt 文字 / 技法 / 章節。
- 每張案例卡可「收藏」與「評分(0-5星)」,評分寫回偏好(供日後個人化排序)。
- 點圖可放大;點 prompt 可一鍵複製。
- 技法詞典與案例書「雙向連結」:卡片上的技法標籤可點 → 跳詞典該技法;詞典技法可點 → 篩案例。

**版面:** 左側可收合的技法詞典樹(~280px) + 右側主案例流(卡片網格,桌面 2-3 欄/手機 1 欄) +
頂部固定搜尋列。深色背景、卡片微陰影、技法標籤用彩色 pill。
---

## 議會 MVP 落地對應（council-api 裁決,我接手實作時用）
- 資料層:SQLite `prompts(id, raw_prompt, tokens, tags, source_url, crawl_ts)` + `images(id, prompt_id, img_url, model, seed, cfg)`(目前 curated.json 已含等價欄位,可直接轉)。
- 先手標 50-100 組高品質樣本當骨幹(每筆 ≥3 技法標籤),再探索自動抽取。
- 缺口待補:①自動更新(incremental_scraper 加排程) ②site/ 重建 ③詞典 hash 跳轉修復。
- 設計稿從 Claude Design 出來後,我負責把它接上 `data/curated.json` + 修上述缺口。
