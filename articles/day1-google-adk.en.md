---
title: "Valid Schema, Wrong Content: Using Jev to Guard a Google ADK Agent"
published: false
description: "A structured-output JSON can pass every schema check and still be unusable. I generated the broken result, verified it with my own subtitle tool, and used TypeSafe's Jev as the QC gate ADK's schema can't be."
tags: ai, googlecloud, python, llm
series: Schema-valid is not content-correct
canonical_url: https://memo.jimmyliao.net/p/jev-google-adk-agent
cover_image: media/cover_jev_01.png
---

*Schema-valid is not content-correct · Part 1/3*

## It starts with a storyboard a video-generation agent produced

Here's a JSON storyboard for a short video, four segments, each tagged with type, duration, and text. The `noul` confidence scores are real Jev API results for the *original Traditional Chinese text* (an English translation of the same words would read at a different pace, so I'm keeping the text as-sent rather than translating it in place — English gloss below each line):

```
[seg-1] title_card  3s  ✅  (confidence=0.44)
    text: 未來已來
    ("The future is already here")
[seg-2] photo       3s  ⚠️ NEEDS REVIEW  (confidence=0.77)
    text: Google ADK 讓開發者只需三行程式碼，就能定義一個具備完整推理、規劃與工具呼叫能力、可對接任意企業系統的生產級自主代理
    ("Google ADK lets developers define a production-grade autonomous agent with full
      reasoning, planning, and tool-calling capability, able to integrate with any
      enterprise system, in just three lines of code")
[seg-3] video_clip  8s  ✅  (confidence=0.45)
    text: 一行指令，Agent 自動完成程式碼生成、測試與部署
    ("One command, and the agent handles code generation, testing, and deployment automatically")
[seg-4] credits     2s  ✅  (confidence=0.57)
    text: 非官方技術示範
    ("Unofficial technical demo")
```

This is the storyboard spec for a sub-20-second short video: four segments, each labeled with type, duration, and text. It's schema-valid — every field is the right type, nothing would make a JSON parser complain.

But read `seg-2`'s line out loud against a 3-second photo: anyone can tell at a glance it won't fit.

Schema validation doesn't catch this. It only checks "is this a legal `photo` object," not "does this `caption` fit inside `duration_sec`." That gap — **schema-valid is not content-correct** — is what this article, and this whole series, is about.

This time we fed all four segments straight into `gemini-omni-1.1-flash`, stitched them into one video, **completely ignoring Jev's warning**, to see what happens:

{% youtube GURAPVvGP68 %}

By the second segment you'll notice it — the narration is visibly rushed, and the scene cuts away mid-sentence.

## Why not just call the Gemini API directly

Honestly, if all you need is "get the model to produce schema-valid JSON," `google-adk` isn't necessary. A bare `google-genai` call to `gemini-3.1-pro-preview` with `response_schema` gets you the same result, with less code:

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

If that's all ADK did in this article, there'd be nothing left to write — just call `gemini-3.1-pro-preview` with `response_schema`, check the result with Jev externally, and call it a post.

### Where ADK actually earns its keep: letting the agent know it might be wrong

ADK's value isn't "producing a JSON blob" — it's **orchestration**: giving an agent tools, letting it perceive what those tools return, and letting it decide its next move based on that. Wrap Jev as an ADK tool, attach it to `director_agent`, and let it self-check:

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
        "You are a professional short-video editor. After planning the video timeline, "
        "call check_segment on every segment to self-check; for any segment flagged "
        "needs_review, regenerate that segment's caption so it reasonably fits "
        "duration_sec, retrying at most twice."
    ),
    tools=[check_segment_tool],
    output_schema=VideoTimeline,
)
```

I wrapped the Jev call as an ADK tool the agent uses to self-check. This way, the ADK agent doesn't just produce a JSON blob — it perceives what the tool returns and decides its next step accordingly.

> The tool-calling version is still being implemented; this post uses the external-call version (`common/jev_client.check_segment`) to demonstrate how Jev itself works.
>
> One verified detail worth adding: pairing `output_schema` with `tools` on the same Agent is officially supported by ADK — the source comment says it works "by exposing tools during the thought loop and enforcing structure only on the final output," which matches this design. But the installed package has a capability check (`gemini_output_schema_and_tools`) that only reports available when running on the **Vertex AI** backend (`GOOGLE_GENAI_USE_VERTEXAI=1`). Whether this combination works with a plain `GOOGLE_API_KEY` (AI Studio / Developer API — what this repo's `.env.example` currently uses) hasn't been live-tested yet; I'll follow up.

## Google ADK: `output_schema`, not `response_schema`

The installed `google-adk` version is `2.7.0`. When calling the API, use `output_schema`, not `response_schema`.

You may have seen something like this:

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

Change it to:

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

## How Jev decides whether the planned text fits the planned duration

`check_segment` sends the segment's duration and text to Jev and asks one `noul` (yes/no) question. The prompt is written in Traditional Chinese on purpose — that's the language of the actual content being judged, and it's what the confidence scores in this post were measured against, so I'm keeping the code exactly as it is in the repo rather than showing a translated (and untested) English version:

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
                        # "Estimating at a natural speaking pace, would reading/speaking this
                        #  text take noticeably longer or shorter than the labeled duration
                        #  (more than roughly 30% off)?"
                    )
                )
            },
            model="jev-latest",
        )
    answer = response.answers["duration_caption_mismatch"]
    return {"needs_review": answer.noul > 0.6, "confidence": answer.noul}
```

The returned `noul` is a probability between 0 and 1 — not a Transformer LLM casually saying "I'd guess 80%." TypeSafe trains this value to be calibrated: when the model says 70%, over the long run it should actually be right about 70% of the time. That's different from reading confidence off an LLM's `logprobs`, which reflect "how common is this token," not "how trustworthy is this judgment."

In the real output at the top of this post, `seg-2` scored `confidence=0.77`, above the 0.6 threshold, and got flagged; the other three stayed below threshold and passed. All four numbers are real API call results — you can rerun them yourself against `common/jev_client.py` in the repo.

## Verifying it with my own auto-subtitle tool, LeapieVideo

Jev says `seg-2` has a problem, but how bad is it? Listening alone isn't precise enough, so I fed the synthesized video above into another project of mine — **LeapieVideo** — and actually transcribed it. This is the real, unedited output (the narration is in Traditional Chinese, since that's the language the video was generated in):

```json
{"start": 2.9,   "end": 4.376,  "text": "Google ADK"},
{"start": 4.376, "end": 5.557,  "text": "讓開發者只需三行"},
{"start": 5.557, "end": 6.557,  "text": "程式碼"},
{"start": 6.557, "end": 8.368,  "text": "一鍵智慧 一鍵執行"}
```

Roughly: "Google ADK — lets developers, in just three — lines of code —" then the scene cuts away. `seg-2`'s timeline only runs to 6.557 seconds. The full line in the original JSON was: "**Google ADK lets developers define a production-grade autonomous agent with full reasoning, planning, and tool-calling capability, able to integrate with any enterprise system, in just three lines of code**" (translated from the Chinese original) — in the actual rendered video, the narration only gets as far as "lets developers, in just three lines of code" before the next scene cuts it off. The rest of the sentence — the part about reasoning, planning, tool-calling, enterprise integration — was never spoken at all.

## Day 1 takeaways

This is part one of the series; the focus is the mechanism itself: the `VideoTimeline` schema, plus using Jev to judge whether a storyboard segment needs to be regenerated, and having ADK evaluate whether its own answer turned out as expected.

Tomorrow: the same schema and the same `check_segment`, unchanged, rebuilt on Microsoft Agent Framework.

---

*Full code: [jimmyliao/jev-storyboard-lab](https://github.com/jimmyliao/jev-storyboard-lab)*
