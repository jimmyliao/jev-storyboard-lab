---
title: "Jev 抓到問題之後：兩種修法，哪個對？"
day: 3
series: "格式合法，不等於內容合理"
author: Jimmy Liao
---

# Jev 抓到問題之後：兩種修法，哪個對？

*格式合法，不等於內容合理 · 系列 3/3*

## 前情提要

Day1、Day2 都在證明同一件事：`VideoTimeline` schema 驗證過關，不代表內容合理——不管分鏡是 Google ADK 生的還是 Microsoft Agent Framework 生的，Jev 都能抓到「文字塞不進秒數」這個問題。

但 Jev 抓到問題之後呢？「抓到」只是第一步，**怎麼修**才是真正要做決定的地方。以 Day2 那個被標記的 `seg-07-credits-cta` 為例：

```
文字: 一份規格，兩套雲端。追蹤看完整實作 ⚡
秒數: 2.0s
jev confidence: 0.70（超過 0.6 門檻，需複查）
```

兩種修法都能讓 Jev 通過，但代價不一樣。

## 修法 A：縮短文字，秒數不變

把文字砍到只留最關鍵的訊息：

```python
from common.jev_client import check_segment

check_segment("seg-07-credits-cta", 2.0, "規格可攜")
# {'needs_review': False, 'confidence': 0.53}
```

代價：資訊量變少，「追蹤看完整實作」這個 CTA 沒了。適合秒數是硬限制的場景（例如廣告版位、固定格式的短影音節奏）。

## 修法 B：延長秒數，保留完整文字

文字完全不動，反過來調整分鏡秒數，抓實際唸完需要的時間：

```python
for dur in [2.0, 2.5, 3.0]:
    check_segment("seg-07-credits-cta", dur,
                  "一份規格，兩套雲端。\n追蹤看完整實作 ⚡")
# 2.0s -> confidence=0.70（不過）
# 2.5s -> confidence=0.69（不過）
# 3.0s -> confidence=0.49（通過）
```

代價：影片總長度變長（這支短影音從 20 秒變成 21 秒），如果總長度是硬限制（例如 YouTube Shorts 上限），就要從別的地方擠出這 1 秒。適合內容不能刪、只是原本規劃的秒數低估的場景。

## 三版並列

<video src="media/day3-comparison.mp4" controls width="360" poster=""></video>

第一段是 Day2 原本超時的版本（2 秒被 API 最低秒數限制拉到 3 秒生成，但敘事節奏仍是設計給 2 秒），第二段是修法 A，第三段是修法 B——**兩種修法都讓 Jev 通過，畫面上也都唸得完，但選哪一種，是產品決策，不是 Jev 能幫你決定的**。Jev 的角色只到「告訴你哪裡有問題、多嚴重」，怎麼取捨是人（或上層的 agent 邏輯）該做的事。

## 如果讓 Agent 自己選

Day1 提過 ADK 支援把 Jev 包成 `FunctionTool`，讓 Agent 自我修正、最多重試兩次——這個機制目前還沒做出「該選哪種修法」的決策邏輯。合理的下一步設計是把這個取捨也變成一條規則：例如「秒數是硬限制時用修法 A，秒數有彈性時用修法 B」，寫進 Agent 的 instruction 裡，讓它自己判斷該砍文字還是該延秒數，而不是永遠只會做同一種修正。這是這個系列之後可以繼續延伸的方向，這篇先把「兩種修法都是合法解」這件事講清楚。

## 系列總結

三天做的事：
- **Day1**：schema-valid 不等於 content-correct，Jev 是 vendor-neutral 的 QC gate
- **Day2**：同一套 Jev 邏輯，換雲端（Gemini→Azure）一行不用改，但踩了兩個雲端限定的 SDK 坑
- **Day3**：Jev 抓到問題只是開始，怎麼修（砍內容 vs. 延時間）是需要額外決策邏輯的地方

完整程式碼、三天的真實 API 呼叫結果，都在 repo 裡可以重跑一次驗證。

---

*完整程式碼：[jimmyliao/jev-storyboard-lab](https://github.com/jimmyliao/jev-storyboard-lab)*
