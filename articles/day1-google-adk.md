---
title: "同一份 JSON，兩種下場：用 Jev 幫 Google ADK 的 Agent 把關"
day: 1
series: "格式合法，不等於內容合理"
author: Jimmy Liao
---

# 用 Jev 幫 Google ADK 的 Agent 把關

## 開場：一份「完全合法」的 JSON

先看一段終端機輸出，不看程式碼：

```
[seg-1] title_card  3s  ✅  (confidence=0.44)
    文字: 未來已來
[seg-2] photo       3s  ⚠️ NEEDS REVIEW  (confidence=0.77)
    文字: Google ADK 讓開發者只需三行程式碼，就能定義一個具備完整推理、規劃與工具呼叫能力、可對接任意企業系統的生產級自主代理
[seg-3] video_clip  8s  ✅  (confidence=0.45)
    文字: 一行指令，Agent 自動完成程式碼生成、測試與部署
[seg-4] credits     2s  ✅  (confidence=0.57)
    文字: Powered by Google ADK
```

這是一支 20 秒短影音的分鏡規格：四個片段，各自標好類型、秒數、文字。全部驗證得過 schema——每個欄位型別都對，沒有任何一個地方會讓 JSON parser 報錯。

但你自己唸一次 `seg-2` 那句文字，配上 3 秒鐘的照片：唸不完。這句話正常語速要 4 秒以上，卻被排進一張只停留 3 秒的照片。

Schema 檢查不會發現這件事——它只管「這是不是一個合法的 `photo` 物件」，不管「這個 `caption` 塞不塞得進 `duration_sec`」。**格式合法，不等於內容合理**。這個落差就是這篇文章、以及接下來這整個系列要處理的東西。

別只相信我這段文字描述——我把這四個片段真的丟給 `gemini-omni-1.1-flash` 生成、串接成一支完整 17 秒的影片，看看**完全不管 Jev 警告**會是什麼下場：

<video src="media/day1-full-raw-cut.mp4" controls width="360" poster=""></video>

*（如果你的閱讀器不放影片，直接看 [`articles/media/day1-full-raw-cut.mp4`](media/day1-full-raw-cut.mp4)；只想看出事的那 3 秒，看 [`day1-seg2-too-long.mp4`](media/day1-seg2-too-long.mp4)）*

播到第二段你會聽出來——旁白明顯在趕，句子講到一半畫面就切走了。

## 為什麼不直接打 Gemini API 就好

老實說，光是「叫模型產生一份符合 schema 的 JSON」這件事，`google-adk` 不是必要的。用最陽春的 `google-genai` SDK，直接打 `gemini-3.1-pro-preview`、帶上 `response_schema`，也能拿到一模一樣的結果，程式碼還更少：

```python
from google import genai

client = genai.Client()
response = client.models.generate_content(
    model="gemini-3.1-pro-preview",
    contents=prompt,
    config={"response_schema": VideoTimeline, "response_mime_type": "application/json"},
)
timeline = VideoTimeline.model_validate_json(response.text)
```

如果 ADK 在這篇文章裡只做這件事，那它就是一個包裝結構化輸出的花俏外殼，禁不起「為什麼不直接打 API」這個問題。所以在往下寫之前，得先把這個問題答清楚。

## ADK 真正該扛的活：讓 Agent 自己知道它可能錯了

ADK 的價值不在「產生一份 JSON」，在**編排**——讓一個 Agent 擁有工具、能感知工具回傳的結果、並根據結果調整自己下一步要做什麼。把 Jev 包成一個 ADK 工具，掛在 `director_agent` 身上，情況就不一樣了：

```python
from google.adk.agents import Agent
from google.adk.tools import FunctionTool

from common.jev_client import check_segment
from common.schemas import VideoTimeline

check_segment_tool = FunctionTool(check_segment)

director_agent = Agent(
    name="director_agent",
    model="gemini-3.1-pro-preview",
    instruction=(
        "你是一位專業的短影音剪輯師。規劃 video timeline 後，"
        "對每一個片段呼叫 check_segment 自我檢查；"
        "任何被標記 needs_review 的片段，重新生成該片段的 caption，"
        "確保跟 duration_sec 合理對齊，最多重試兩次。"
    ),
    tools=[check_segment_tool],
    output_schema=VideoTimeline,
)
```

現在 Jev 不是外部 Python 迴圈呼叫的東西，是 **Agent 自己會用的工具**。這才是 ADK 的 `tools=[...]` 該扛的活，也才回答得了「為什麼不直接打 API」：因為你要的不是一次性生成一份 JSON，是一個**會自我校正的 Agent**。

> 這個 tool-calling 版本目前還在實作中，本文先用外部呼叫版本（`common/jev_client.check_segment`，程式碼跟上面終端機輸出用的完全相同）示範 Jev 本身怎麼運作；完整的自我校正版本，等這系列走到收尾時會補進 repo。

## `output_schema`，不是 `response_schema`

寫這篇之前，我实際裝了 `google-adk` 2.9.2，用 `inspect` 反查過 `Agent` 這個 class 真正的欄位：

```python
>>> from google.adk.agents import Agent
>>> list(Agent.model_fields.keys())
[..., 'input_schema', 'output_schema', 'state_schema', ...]
```

真正的欄位名是 `output_schema`。如果你看到哪篇文章寫 `response_schema=...`，那是錯的——這個欄位在目前版本的 ADK 裡不存在，設了也不會報錯，只是安靜地被忽略。這是最容易踩的坑：你以為自己有 schema 約束，實際上完全沒有，Agent 想生什麼就生什麼。

## Jev 怎麼判斷「塞不塞得下」

`check_segment` 本身很單純，就是把片段的秒數跟文字丟給 Jev，問一個 `noul`（是非題）：

```python
def check_segment(segment_id: str, duration_sec: float, caption: str | None) -> dict:
    if not caption:
        return {"needs_review": False, "confidence": 0.0}

    state = f"片段 {segment_id}：標註時長 {duration_sec} 秒，畫面文字/旁白「{caption}」"
    answers = ask(state, {
        "duration_caption_mismatch": {
            "type": "noul",
            "instructions": (
                "以正常中文語速估算，讀完/唸完這段文字所需時間，"
                "是否明顯超過或短於標註的秒數（誤差超過約 30%）？"
            ),
        }
    })
    answer = answers["duration_caption_mismatch"]
    return {"needs_review": answer["noul"] > 0.6, "confidence": answer["noul"]}
```

回傳的 `noul` 是一個 0-1 的機率值，不是模型隨口說的「我覺得 80% 像」——TypeSafe 把這個機率值訓練的目標本身就是校準（calibration）：模型說 70% 的時候，長期而言應該真的有 70% 是對的。這跟一般 LLM 用 `logprobs` 反推信心值不一樣，`logprobs` 反映的是「這個 token 有多常見」，不是「這個判斷有多可信」。

開頭那組真實輸出裡，`seg-2` 拿到 `confidence=0.77`，超過 0.6 的門檻被標記；其他三個都在門檻以下、判定正常。這四個數字全部是真的 API 呼叫結果，可以直接拿 repo 裡的 `common/jev_client.py` 重跑一次驗證。

## 拿自己的字幕工具倒過來驗證

Jev 說 `seg-2` 有問題，但「有問題」到底有多嚴重？光聽耳朵判斷不夠精確，我把上面那支合成影片丟進我自己另一個專案——[liaostudio](https://github.com/jimmyliao/liaostudio)（一個 Whisper/Gemini 字幕產生工具）——實際轉錄一次，逐句時間戳自己會說話：

```json
{"start": 2.9,   "end": 4.376,  "text": "Google ADK"},
{"start": 4.376, "end": 5.557,  "text": "讓開發者只需三行"},
{"start": 5.557, "end": 6.557,  "text": "程式碼"},
{"start": 6.557, "end": 8.368,  "text": "一鍵智慧 一鍵執行"}
```

`seg-2` 對應的時間軸只到 6.557 秒。原本 JSON 裡那句完整文字是「**Google ADK 讓開發者只需三行程式碼，就能定義一個具備完整推理、規劃與工具呼叫能力、可對接任意企業系統的生產級自主代理**」——實際生出來的影片裡，旁白只唸到「讓開發者只需三行程式碼」就被下一段畫面截斷，後面一大串「就能定義一個具備完整推理、規劃與工具呼叫能力……」**整句話從頭到尾沒有被唸出來**。

這不是我事後腦補的效果，是拿自己另一個生產工具轉錄出來的真實結果，剛好印證了 Jev 當初給的 `confidence=0.77`：這句文字，塞不進 3 秒鐘。

## 收尾

今天的重點是機制本身：一顆兩篇都要共用的 `VideoTimeline` schema，一支 Jev QC 工具，還有「ADK 憑什麼」這個問題的誠實答案。明天把完全相同的 schema 跟 `check_segment`，原封不動搬到 Azure AI Foundry，用 Microsoft Agent Framework 重做一次——順便揭曉，這兩篇之間，`jev_client.py` 到底要改幾行。

---

*完整程式碼：[jimmyliao/jev-storyboard-lab](https://github.com/jimmyliao/jev-storyboard-lab)*
