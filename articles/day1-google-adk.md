---
title: "同一份 JSON，兩種下場：用 Jev 幫 Google ADK 的 Agent 把關"
day: 1
series: "格式合法，不等於內容合理"
author: Jimmy Liao
---

# 用 Jev 幫 Google ADK 的 Agent 把關

*格式合法，不等於內容合理 · 系列 1/3*

## 從 AI 自動生成影片的分鏡內容開始

我們來看一個短影片的 JSON 分鏡，預計規劃會生成的文字/聲音：

```
[seg-1] title_card  3s  ✅  (confidence=0.44)
    文字: 未來已來
[seg-2] photo       3s  ⚠️ NEEDS REVIEW  (confidence=0.77)
    文字: Google ADK 讓開發者只需三行程式碼，就能定義一個具備完整推理、規劃與工具呼叫能力、可對接任意企業系統的生產級自主代理
[seg-3] video_clip  8s  ✅  (confidence=0.45)
    文字: 一行指令，Agent 自動完成程式碼生成、測試與部署
[seg-4] credits     2s  ✅  (confidence=0.57)
    文字: 非官方技術示範
```

這是一支 20 秒內短影片的分鏡規格：四個片段，分別標註了類型、秒數、文字。

但你自己唸一次 `seg-2` 那句文字，配上 3 秒鐘的照片：人一判斷就知道一定是唸不完。

而 Schema 檢查時，並不會發現這件事。這篇文章、以及接下來這整個系列要處理的東西，就是這個落差：如何用 AI 本身建構出比 Schema 更嚴格的防護網。

這一篇我們就把這四個片段直接呼叫 `gemini-omni-1.1-flash` 生成、串接成一支完整影片，**完全不管 Jev 警告**，看看會是什麼下場：

<video src="media/day1-full-raw-cut.mp4" controls width="360" poster=""></video>

播到第二段時，你會知道，句子講到一半時，畫面就切走了。

## 為什麼不直接呼叫 Gemini API 就好

因為，光是「叫模型產生一份符合 schema 的 JSON」這件事，`google-adk` 不是必要的。用最陽春的 `google-genai` SDK，直接打 `gemini-3.1-pro-preview`、帶上 `response_schema`，也能拿到一模一樣的結果，程式碼還更少：

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

如果 ADK 在這篇文章裡只做這件事，那就真的沒什麼好寫的了，我們直接用 `gemini-3.1-pro-preview` 搭配 `response_schema` 產生分鏡，再用 Jev 外部檢查，把結果做成一篇文章就好。

### ADK 真正有價值的應用場景是：**讓 Agent 自己知道它可能錯了**。

ADK 的價值不在「產生一份 JSON」，是**編排** 讓一個 Agent 可以透過**工具**，感知工具回傳的結果、並根據結果調整自己下一步要做什麼。

我們試著把這幾天正在熱門討論的 [Jev](https://typesafe.ai) 建構出的各類檢查工具，包成一個 ADK 工具，掛在 `director_agent` 身上，然後讓它自我檢查：

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

我將 Jev 呼叫包裝成 ADK tool 提供給 Agent 用來作自我檢查的工具。透過這種方式，ADK 的 Agent 不只能產生一份 JSON，還能感知工具回傳的結果、並根據結果調整自己下一步要做什麼。

> tool-calling 版本目前還在實作中，這次就用外部呼叫版本，可以參考（`common/jev_client.check_segment`）示範 Jev 本身怎麼運作。
>
> 補一個查證過的細節：`output_schema` 跟 `tools` 掛在同一個 Agent 上，ADK 官方是支援的——原始碼裡的說明是「在思考迴圈中暴露工具，只在最終輸出時強制套用結構」，跟這裡的設計對得上。但裝好的套件裡有一個能力檢查（`gemini_output_schema_and_tools`），只有走 **Vertex AI** 後端（`GOOGLE_GENAI_USE_VERTEXAI=1`）才會回傳可用；單純用 `GOOGLE_API_KEY`（AI Studio／Developer API，也就是本文 `.env.example` 目前寫的方式）這個組合能不能用，還沒實測驗證過，之後補上。


## Google ADK 的 `output_schema` != `response_schema`

裝的 `google-adk` 版本是 `2.7.0`，記得呼叫 API 時要用 `output_schema`，不是 `response_schema`。

你可能在官網看過類似下面的寫法：

```python
from google.adk.agents import Agent
from common.schemas import VideoTimeline

agent = Agent(
    name="agent",
    model="model",
    instruction="",
    response_schema=VideoTimeline,
)
```

改成

```python
from google.adk.agents import Agent
from common.schemas import VideoTimeline

agent = Agent(
    name="agent",
    model="model",
    instruction="",
    output_schema=VideoTimeline,
)
```


## Jev 怎麼判斷排定的分鏡文字內容「塞不塞得下」預定的影片長度

`check_segment` 本身很單純，就是把片段的秒數跟文字丟給 Jev，問一個 `noul`（是非題）。第一版是自己拿 `httpx` 手刻 REST 呼叫，後來發現 TypeSafe 有[官方 Python SDK](https://docs.typesafe.ai/sdk/python)（`pip install typesafe-sdk`），乾脆直接改用官方的：

```python
from typesafe_sdk import Noul, TypeSafeClient

def check_segment(segment_id: str, duration_sec: float, caption: str | None) -> dict:
    if not caption:
        return {"needs_review": False, "confidence": 0.0}

    state = f"片段 {segment_id}：標註時長 {duration_sec} 秒，畫面文字/旁白「{caption}」"
    with TypeSafeClient() as client:
        response = client.system_one(
            state=state,
            questions={
                "duration_caption_mismatch": Noul(
                    instructions=(
                        "以正常中文語速估算，讀完/唸完這段文字所需時間，"
                        "是否明顯超過或短於標註的秒數（誤差超過約 30%）？"
                    )
                )
            },
            model="jev-latest",
        )
    answer = response.answers["duration_caption_mismatch"]
    return {"needs_review": answer.noul > 0.6, "confidence": answer.noul}
```

回傳的 `noul` 是一個 0-1 的機率值，不是 Transformer LLM 隨口回答「我覺得 80% 像」，TypeSafe 會把這個機率值訓練到讓它本身就是校準（calibration）：模型說 70% 的時候，長期而言就是有 70% 是對的。這跟一般 LLM 用 `logprobs` 反推信心值不一樣，`logprobs` 反映的是「這個 token 有多常見」，不是「這個判斷有多可信」。

開頭那組真實輸出裡，`seg-2` 拿到 `confidence=0.77`，超過 0.6 的門檻被標記；其他三個都在門檻以下、判定正常。這四個數字全部是真的 API 呼叫結果，可以直接拿 repo 裡的 `common/jev_client.py` 重跑一次驗證。

## 拿我前陣子自己開發的影片自動轉字幕工具，當作驗證參考

Jev 說 `seg-2` 有問題，但「有問題」到底有多嚴重？光聽耳朵判斷不夠精確，我把上面那支合成影片丟進我自己另一個專案——[liaostudio](https://github.com/jimmyliao/liaostudio)（一個 Whisper/Gemini 字幕產生工具）——實際轉錄一次，逐句時間戳自己會說話：

```json
{"start": 2.9,   "end": 4.376,  "text": "Google ADK"},
{"start": 4.376, "end": 5.557,  "text": "讓開發者只需三行"},
{"start": 5.557, "end": 6.557,  "text": "程式碼"},
{"start": 6.557, "end": 8.368,  "text": "一鍵智慧 一鍵執行"}
```

`seg-2` 對應的時間軸只到 6.557 秒。原本 JSON 裡那句完整文字是「**Google ADK 讓開發者只需三行程式碼，就能定義一個具備完整推理、規劃與工具呼叫能力、可對接任意企業系統的生產級自主代理**」——實際生出來的影片裡，旁白只唸到「讓開發者只需三行程式碼」就被下一段畫面截斷，後面一大串「就能定義一個具備完整推理、規劃與工具呼叫能力……」**整句話從頭到尾沒有被唸出來**。

## Day1 心得

這邊是系列文的第一篇，重點是機制本身：`VideoTimeline` schema，加上 Jev QC 評判是否需要重新生成分鏡片段，以及 ADK 評估自身回答是否如預期。

明天會將同樣的 schema 跟 `check_segment`，原封不動改用 Microsoft Agent Framework 重做一次。

---

*完整程式碼：[jimmyliao/jev-storyboard-lab](https://github.com/jimmyliao/jev-storyboard-lab)*
