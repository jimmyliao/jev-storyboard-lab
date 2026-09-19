"""Run the Microsoft Agent Framework director agent, then QC every segment with Jev.

Requires an Azure OpenAI / Azure AI Foundry resource with a structured-
output-capable deployment (GPT-4o-2024-08-06+ or GPT-5.x):
  FOUNDRY_PROJECT_ENDPOINT   — e.g. https://your-resource.services.ai.azure.com/openai/v1
  FOUNDRY_MODEL              — your deployment name
  FOUNDRY_API_KEY            — the resource's API key
  TYPESAFE_API_KEY           — https://console.typesafe.ai

Usage:
  uv run python -m agent_framework_demo.main "20 秒的 YouTube Shorts，主題是 Microsoft Agent Framework 的 structured output"
"""

import asyncio
import sys

from agent_framework_demo.director_agent import build_director_agent
from common.jev_client import check_segment
from common.schemas import VideoTimeline


async def generate_timeline(prompt: str) -> VideoTimeline:
    agent = build_director_agent()
    response = await agent.run(prompt)
    # `.value` is a VideoTimelineAzure (the Azure-compatible wire schema,
    # see schemas.py) — round-trip it into the canonical VideoTimeline
    # that check_segment and every downstream step expects. Pydantic's
    # discriminated-union validator works fine on this dict; the
    # discriminator is only unusable for schema *generation*, not parsing.
    return VideoTimeline.model_validate(response.value.model_dump())


async def main(prompt: str) -> None:
    timeline = await generate_timeline(prompt)

    print(f"🎬 {timeline.title}  ({timeline.total_duration_sec}s, {timeline.target_platform})\n")

    flagged = 0
    for seg in timeline.segments:
        result = check_segment(seg.id, seg.duration_sec, seg.caption)
        mark = "⚠️ NEEDS REVIEW" if result["needs_review"] else "✅"
        if result["needs_review"]:
            flagged += 1
        print(
            f"[{seg.id}] {seg.type} {seg.duration_sec}s  {mark}  "
            f"(jev confidence={result['confidence']:.2f})\n"
            f"    文字: {seg.caption or '(無)'}\n"
        )

    print(f"共 {len(timeline.segments)} 個片段，{flagged} 個被 Jev 標記需要人工複查。")


if __name__ == "__main__":
    prompt = " ".join(sys.argv[1:]) or (
        "請幫我規劃一支 20 秒的 YouTube Shorts video timeline，主題是"
        "『同一份規格，兩套雲端：用 Microsoft Agent Framework 重現昨天的 ADK 導演 Agent』，"
        "要求 Cyberpunk 科技感。"
    )
    asyncio.run(main(prompt))
