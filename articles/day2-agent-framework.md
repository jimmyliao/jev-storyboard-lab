---
title: "同一份規格，兩套雲端：Microsoft Agent Framework 重現昨天的 ADK Agent"
day: 2
series: "格式合法，不等於內容合理"
author: Jimmy Liao
---

# 用 Jev 幫 Microsoft MAF 的 Agent 把關

*格式合法，不等於內容合理 · 系列 2/3*

## 昨天那段程式碼，今天原封不動搬過來——只有一半是真的

昨天用 [Google ADK](https://memo.jimmyliao.net/p/jev-google-adk-agent) 產生 `VideoTimeline`、透過 Jev 檢查 `seg-2` 應該要被修改的邏輯。今天換個目標：同樣的檢查，但是改用 Microsoft Agent Framework (MAF)。

以下是我採雷經驗分享跟成果:

## `FoundryChatClient` 需要 Azure AD，不吃 API key

Agent Framework 官方的 Azure client 是 `agent_framework.foundry.FoundryChatClient`。查了原始碼，它的 `credential` 參數型別是：

```python
AzureCredentialTypes = TokenCredential | AsyncTokenCredential
```

**這表示 MAF 只能用 Azure AD 憑證**（`az login` 或 service principal），而常用的 API key 是不行的。

Workaround： MAF 有 `agent_framework.openai.OpenAIChatClient`，支援 `api_key` + `base_url` 直接指定。
另外 Azure endpoint 記得將指向 （`https://<resource>.services.ai.azure.com/openai/v1`）

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

## Pydantic discriminated union 透過 Azure foundry structured output 回傳 400

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

解決方式就是拿掉 discriminator，改成單純 `Union` (不會影響後面 rebuild  `VideoTimeline`)

```python
response = await agent.run(prompt)
timeline = VideoTimeline.model_validate(response.value.model_dump())
```

## `jev_client.py`

`check_segment()` 直接使用昨天同一份，包括 `VideoTimeline`，透過 Jev 串接到後面的 LLM endpoint 達到可以互換 Gemini / Azure foundry endpoint。

```python
from common.jev_client import check_segment

for seg in timeline.segments:
    result = check_segment(seg.id, seg.duration_sec, seg.caption)
```

## 實際測試結果

```
🎬 同個 schema，用兩種 Agent framework libraries：Microsoft Agent Framework 重現 ADK 導演 Agent  (20s, YouTube Shorts（9:16）)

[seg-01-neon-hook]        title_card 2.0s  ✅  (jev confidence=0.50)
    文字: 同一份 Agent 規格 能跨雲重現嗎？
[seg-02-adk-blueprint]    video_clip 3.0s  ✅  (jev confidence=0.48)
    文字: 昨天：用 ADK 打造「導演 Agent」
[seg-03-spec-core]        photo      3.0s  ✅  (jev confidence=0.43)
    文字: 保留核心規格：角色、流程、工具、輸出
[seg-04-framework-switch] video_clip 4.0s  ✅  (jev confidence=0.41)
    文字: 今天切換 Microsoft Agent Framework 重新接上模型與工具
[seg-05-orchestration]    video_clip 3.0s  ✅  (jev confidence=0.47)
    文字: 讓 Agent 拆解任務、調度步驟、整合結果
[seg-06-result]           photo      3.0s  ✅  (jev confidence=0.41)
    文字: 框架不同，導演邏輯依然可重現
[seg-07-credits-cta]      credits    2.0s  ⚠️ NEEDS REVIEW  (jev confidence=0.70)
    文字: 一份規格，兩套雲端。追蹤看完整實作 ⚡

共 7 個片段，1 個被 Jev 標記需要人工複查。
```

這是真的打 Azure 端到端跑出來的結果，不是編的——`seg-07-credits-cta` 那個 2 秒的 credits 卡片被標到 0.70，塞了「一份規格，兩套雲端。追蹤看完整實作」這句進 2 秒鐘，跟昨天 `seg-2` 是同一種毛病，只是這次是 Microsoft 的雲、Azure 的模型生出來的。

同樣**完全不管 Jev 警告**，把這七段直接餵給 `gemini-omni-1.1-flash` 生成、串接成一支完整影片：

<video src="media/day2-full-raw-cut.mp4" controls width="360" poster=""></video>

播到最後那張 credits 卡片時，字幕/旁白明顯被截斷——跟 Day1 的 `seg-2` 是同一種症狀，只是這次發生在片尾而不是片中。

---

*完整程式碼：[jimmyliao/jev-storyboard-lab](https://github.com/jimmyliao/jev-storyboard-lab)*
