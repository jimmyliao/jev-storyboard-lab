---
title: "Jev 抓到問題之後：兩種修法，哪個對？"
day: 3
series: "格式合法，不等於內容合理"
author: Jimmy Liao
cover_image: media/cover_jev_03.png
---

# Jev 抓到影片分鏡文字超時之後，該怎麼修？

*格式合法，不等於內容合理 · 系列 3/3*

## 前情提要

Day1、Day2 都在證明同一件事：`VideoTimeline` schema 驗證過關，不代表內容合理——不論是 Google ADK, 還是 Microsoft Agent Framework，都能透過 Jev 抓到文字量過大，塞不進影片這個問題。

抓到問題之後呢？「抓到」只是第一步，**怎麼修**才是真正要做決定的地方。以 Day2 為例：

```
文字: 一份規格，兩套雲端。追蹤看完整實作 ⚡
秒數: 2.0s
jev confidence: 0.70（超過 0.6 門檻，需複查）
```

我們來看看兩種修法，當然分別有不同取捨。

## 文句縮短，想辦法維持秒數

根據目標時間內，把文字精簡:

```python
from common.jev_client import check_segment

check_segment("seg-07-credits-cta", 2.0, "規格可攜")
# {'needs_review': False, 'confidence': 0.53}
```

取捨：資訊量變少，**重點訊息「追蹤看完整實作」**沒了。

## 保留完整文字，適度延長影片時間:

文字完全不動，反過來調整分鏡秒數，抓實際唸完需要的時間：

```python
for dur in [2.0, 2.5, 3.0, 3.5, 4.0, 4.5, 5.0, 5.5, 6.0]:
    check_segment("seg-07-credits-cta", dur,
                  "一份規格，兩套雲端。\n追蹤看完整實作 ⚡")
# 2.0s -> confidence=0.70（不過）
# 2.5s -> confidence=0.69（不過）
# 3.0s -> confidence=0.51（通過）
# 4.0s -> confidence=0.43
# 5.0s -> confidence=0.43
# 6.0s -> confidence=0.41
```

取捨：影片總長度變長，如果總長度是硬限制（例如 YouTube Shorts 上限），就要從別的地方擠出多出來的秒數。不過適合的場景可以是：重點文字內容保留。

後來實驗：本地跑 `faster-whisper`，逐一轉錄：

```
原版（3.0s clip，jev confidence=0.70）
  [0.00 -> 2.40] 一份規格 兩套雲端
  → 話沒講完，「追蹤看完整實作」整句沒出現

修法 A（3.5s clip，jev confidence=0.41）
  [0.00 -> 2.12] （辨識度低，內容不清楚）
  → 時間上沒被截斷（2.12s < 3.5s），但語音本身聽起來含糊

修法 B（5.0s clip，jev confidence=0.43）
  [0.00 -> 4.56] 一份規格 兩套雲端 追蹤看完整實作
  → 完整句子都講出來了，還留了 0.44 秒緩衝
```

這次是真的驗證過的結果：**修法 B 的好處是將完整文句完整的呈現**。

## 三版並列

- 第一段 (00:00 - 00:03)：Day2 原本超時的版本（2 秒被 API 最低秒數限制拉到 3 秒生成，但敘事節奏仍是設計給 2 秒，confidence=0.70，Whisper 驗證確實沒講完）
- 第二段 (00:03 - 00:06)：修法 A（3.5 秒，confidence=0.41）
- 第三段 (00:06 - 00:11)：修法 B（5 秒，confidence=0.43，Whisper 驗證確實講完整句）

修法抉擇: Jev 只能「告訴你哪裡有問題、多嚴重」，怎麼取捨是由 agent （或人定義的邏輯）決定。

<video src="media/day3-comparison.mp4" controls width="360" poster=""></video>

## 如果讓 Agent 自行決定

這系列先利用 Jev 與 Google/Microsoft Agent Framework (Google ADK, MAF) 針對影片生成編輯進行初探。關於「讓 Agent 自行決定修法」這個功能，尚未實作。

但 Day1 提過 ADK 支援把 Jev 包成 `FunctionTool`，讓 Agent 自我修正、最多重試兩次。合理的下一步設計是把這個取捨也變成一條規則：例如「秒數是硬限制時用修法 A，秒數有彈性時用修法 B」，寫進 Agent 的 instruction 裡，讓它自己判斷該砍文字還是該延秒數，而不是永遠只會做同一種修正。

## 系列總結

三天做的事：
- **Day1**：schema-valid 不等於 content-correct，Jev 是 vendor-neutral 的 QC gate
- **Day2**：同一套 Jev 邏輯，換雲端（Gemini→Azure）一行不用改，但踩了兩個雲端限定的 SDK 坑
- **Day3**：Jev 抓到問題只是開始，怎麼修（砍內容 vs. 延時間）是需要額外決策邏輯的地方

完整程式碼、三天的真實 API 呼叫結果，都在 repo 裡可以重跑一次驗證。

---

*完整程式碼：[jimmyliao/jev-storyboard-lab](https://github.com/jimmyliao/jev-storyboard-lab)*
