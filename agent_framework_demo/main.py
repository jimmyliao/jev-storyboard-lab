"""Run the Microsoft Agent Framework director agent, then QC every segment with Jev.

Requires an Azure AI Foundry project with a structured-output-capable
deployment (GPT-4o-2024-08-06+ or GPT-5.x):
  AZURE_AI_PROJECT_ENDPOINT
  AZURE_AI_MODEL_DEPLOYMENT_NAME
  TYPESAFE_API_KEY          — https://console.typesafe.ai
  (Azure auth via `az login` / DefaultAzureCredential — see README)

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
    # `.value` is the schema-validated object when `response_format` is set
    # on ChatOptions — the Agent Framework twin of ADK's `event.output`.
    return response.value


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
