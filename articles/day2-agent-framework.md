---
title: "同一份規格，兩套雲端：Microsoft Agent Framework 重現昨天的 ADK Agent"
day: 2
series: "格式合法，不等於內容合理"
author: Jimmy Liao
---

# Microsoft Agent Framework 重現昨天的 ADK Agent

*格式合法，不等於內容合理 · 系列 2/3*

## 昨天那段程式碼，今天原封不動搬過來——只有一半是真的

昨天用 ADK 產生 `VideoTimeline`、被 Jev 抓到 `seg-2` 唸不完。今天原本的計畫很單純：同一顆 schema，換成 Microsoft Agent Framework 打 Azure，重跑一次，秀一張「兩邊程式碼長不一樣，但 `jev_client.py` 一行沒改」的對照表收工。

**實測之後發現沒那麼單純**——換雲端不是只換 SDK 呼叫方式，schema 本身也踩到一個真的相容性問題。誠實面對這件事,比硬凹「完全零改動」更值得寫。

## 第一個坑：`FoundryChatClient` 需要 Azure AD，不吃 API key

Agent Framework 官方的 Azure client 是 `agent_framework.foundry.FoundryChatClient`。查了原始碼，它的 `credential` 參數型別是：

```python
AzureCredentialTypes = TokenCredential | AsyncTokenCredential
```

**只吃 Azure AD 憑證**（`az login` 或 service principal），不吃一般的 API key。我手上只有一把傳統的 `AZURE_OPENAI_API_KEY`，兩者天生不相容——不是少一個環境變數的問題，是驗證機制完全不同這條路。

繞過方法：Agent Framework 也有 `agent_framework.openai.OpenAIChatClient`，支援 `api_key` + `base_url` 直接指定，而 Azure 現在的新版 endpoint（`https://<resource>.services.ai.azure.com/openai/v1`）本身就是 OpenAI 相容格式：

```python
from agent_framework import Agent, ChatOptions
from agent_framework.openai import OpenAIChatClient

client = OpenAIChatClient(
    model=os.environ.get("FOUNDRY_MODEL"),
    api_key=os.environ.get("FOUNDRY_API_KEY"),
    base_url=os.environ.get("FOUNDRY_PROJECT_ENDPOINT"),
)
director_agent = Agent(
    client=client,
    instructions=INSTRUCTIONS,
    name="director_agent",
    default_options=ChatOptions(response_format=VideoTimelineAzure),
)
```

不用 `az login`，純 API key，跟你手上任何一個 Azure OpenAI 資源都能直接接上。

## 第二個坑：discriminated union 在 Azure 這邊直接 400

昨天的 `VideoTimeline.segments` 用 Pydantic 的 discriminated union（`Field(discriminator="type")`）。Gemini/ADK 吃得下，但把同一顆 schema 綁到 `response_format`，Azure 直接回錯：

```
openai.BadRequestError: Error code: 400 - {'error': {'message':
"Invalid schema for response_format 'VideoTimeline': In
context=('properties', 'segments', 'items'), 'oneOf' is not permitted."}}
```

Pydantic 的 discriminated union 會產生 JSON Schema 的 `oneOf`，但 OpenAI/Azure 的 structured output 嚴格模式**不允許 `oneOf`**，只接受 `anyOf`。拿掉 discriminator、改成單純 `Union`，schema 就會變成 `anyOf`：

```python
# agent_framework_demo/schemas.py
class VideoTimelineAzure(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: str
    target_platform: str
    total_duration_sec: int
    segments: list[Union[TitleCardSegment, PhotoSegment, VideoClipSegment, CreditsSegment]]
```

同樣四個 segment 類型、同樣的欄位，只是拿掉 discriminator 提示。這樣 Azure 就接受了。

**這不代表 schema「不能共用」**——`VideoTimelineAzure` 只是拿來綁 `response_format` 的 wire schema，拿到 Azure 回傳的 JSON 之後，直接轉回昨天那顆 canonical `VideoTimeline`：

```python
response = await agent.run(prompt)
timeline = VideoTimeline.model_validate(response.value.model_dump())
```

Pydantic 的 discriminated union 驗證器在**解析**輸入資料時完全沒問題，只有在**產生** JSON Schema 要求模型輸出時才會撞到 `oneOf` 限制。換句話說：discriminator 對「這是不是合法資料」這件事沒差，只對「我要不要求模型自己標注是哪一種」有差。

## `jev_client.py` 真的一行沒改

把上面兩個坑填完之後，才輪到原本要講的重點——`check_segment()` 全文照搬：

```python
from common.jev_client import check_segment

for seg in timeline.segments:
    result = check_segment(seg.id, seg.duration_sec, seg.caption)
```

跟昨天 ADK 那篇用的是**同一個 import、同一支函式**，Jev 不知道、也不需要知道上面這份 `VideoTimeline` 是 Gemini 生的還是 Azure 生的。

## 實測結果：8 個片段，2 個被抓到

```
🎬 同一份規格，兩套雲端：Microsoft Agent Framework 重現 ADK 導演 Agent  (20s, YouTube Shorts)

[seg-01] title_card 2.0s  ✅  (jev confidence=0.52)
[seg-02] video_clip 3.0s  ✅  (jev confidence=0.54)
[seg-03] photo 3.0s  ✅  (jev confidence=0.44)
[seg-04] video_clip 4.0s  ✅  (jev confidence=0.46)
[seg-05] photo 3.0s  ✅  (jev confidence=0.42)
[seg-06] video_clip 3.0s  ✅  (jev confidence=0.50)
[seg-07] title_card 1.5s  ⚠️ NEEDS REVIEW  (jev confidence=0.62)
    文字: 結論：規格可攜
    實作細節要適配
[seg-08] credits 0.5s  ⚠️ NEEDS REVIEW  (jev confidence=0.84)
    文字: 訂閱看完整實作

共 8 個片段，2 個被 Jev 標記需要人工複查。
```

這是真的打 Azure 端到端跑出來的結果，不是編的——`seg-08` 那個 0.5 秒的 credits 卡片被標到 0.84，塞了「訂閱看完整實作」六個字進半秒鐘，跟昨天 `seg-2` 是同一種毛病，只是這次是 Microsoft 的雲、Azure 的模型生出來的。

## Day 2 心得

昨天講「ADK 憑什麼」，今天講「換雲要付出什麼代價」——代價不是 `jev_client.py`（那顆真的沒變），是 wire schema 要為了廠商的 structured output 限制做一次轉換，而且要驗證過信任的憑證管道對不對得上你手上實際擁有的憑證。這兩個坑都不是查文件能提前知道的，是打下去才知道的。

明天把通過 Jev 檢查的 `VideoTimeline`，真的拿去生一支完整的影片。

---

*完整程式碼：[jimmyliao/jev-storyboard-lab](https://github.com/jimmyliao/jev-storyboard-lab)*
