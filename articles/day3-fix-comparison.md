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

Day1、Day2 都在證明同一件事：`VideoTimeline` schema 驗證過關，不代表內容合理——不管分鏡是 Google ADK 生的還是 Microsoft Agent Framework 生的，Jev 都能抓到「文字塞不進秒數」這個問題。

但 Jev 抓到問題之後呢？「抓到」只是第一步，**怎麼修**才是真正要做決定的地方。以 Day2 那個被標記的 `seg-07-credits-cta` 為例：

```
文字: 一份規格，兩套雲端。追蹤看完整實作 ⚡
秒數: 2.0s
jev confidence: 0.70（超過 0.6 門檻，需複查）
```

兩種修法都能讓 Jev 通過，但代價不一樣。

## 修法 A：縮短文字，秒數不變（後來又多留了一點緩衝）

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

代價：影片總長度變長，如果總長度是硬限制（例如 YouTube Shorts 上限），就要從別的地方擠出多出來的秒數。適合內容不能刪、只是原本規劃的秒數低估的場景。

**有個意外發現**：秒數從 3 秒一路拉到 6 秒，confidence 只從 0.51 掉到 0.41，沒有繼續往下探——**Jev 對「秒數餘裕」的信心提升是有報酬遞減的，不是秒數越長分數就一路變好**。這代表光靠「拉長秒數直到 Jev 說 OK」不是萬靈丹，最後拿掉的 A/B 兩版都改用比剛好通過門檻更保守一點的秒數（A：3.5s，B：5s），留一點安全邊際。

**另外一個誠實的失敗**：原本想拿 Gemini 直接轉錄影片配音，實際核對「Jev 說能唸完」跟「真的有唸完」是不是一致，結果兩次呼叫回傳幾乎一模一樣的逐字稿，明顯是模型照著我 prompt 裡提到的秒數資訊編出來的答案，不是真的在聽音檔——這次沒有可靠的轉錄工具可以驗證，所以「畫面上真的唸完了沒」這件事，這篇文章沒辦法給你一個查證過的答案，只能給到「Jev 預測分數變好了」這一層。這正好呼應這系列的主題：**Jev 的分數是預測，不是保證**，跟 Day1 用 LeapieVideo 實際轉錄核對的精神一樣，這次工具不到位，就老實承認查不到，不硬掰一個聽起來合理的轉錄結果。

## 三版並列

<video src="media/day3-comparison.mp4" controls width="360" poster=""></video>

第一段是 Day2 原本超時的版本（2 秒被 API 最低秒數限制拉到 3 秒生成，但敘事節奏仍是設計給 2 秒，confidence=0.70），第二段是修法 A（3.5 秒，confidence=0.41），第三段是修法 B（5 秒，confidence=0.43）——**兩種修法都讓 Jev 通過，但「唸得完」是 Jev 的預測，不是我這邊實際核對過的事實**（前面那段轉錄失敗的誠實記錄）。選哪一種修法，是產品決策，不是 Jev 能幫你決定的；Jev 的角色只到「告訴你哪裡有問題、多嚴重」，怎麼取捨是人（或上層的 agent 邏輯）該做的事。

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
