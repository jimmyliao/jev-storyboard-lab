"""Run the Microsoft Agent Framework director agent, then QC every scene with Jev.

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
from common.jev_client import check_scene
from common.schemas import VideoStoryboard


async def generate_storyboard(prompt: str) -> VideoStoryboard:
    agent = build_director_agent()
    response = await agent.run(prompt)
    # `.value` is the schema-validated object when `response_format` is set
    # on ChatOptions — the Agent Framework twin of ADK's `event.output`.
    return response.value


async def main(prompt: str) -> None:
    storyboard = await generate_storyboard(prompt)

    print(f"🎬 {storyboard.video_title}  ({storyboard.total_duration_seconds}s, {storyboard.target_platform})\n")

    flagged = 0
    for scene in storyboard.scenes:
        result = check_scene(scene.scene_number, scene.duration_seconds, scene.voiceover)
        mark = "⚠️ NEEDS REVIEW" if result["needs_review"] else "✅"
        if result["needs_review"]:
            flagged += 1
        print(
            f"[{scene.scene_number}] {scene.duration_seconds}s  {mark}  "
            f"(jev confidence={result['confidence']:.2f})\n"
            f"    畫面: {scene.visual_description}\n"
            f"    旁白: {scene.voiceover or '(無旁白)'}\n"
        )

    print(f"共 {len(storyboard.scenes)} 個分鏡，{flagged} 個被 Jev 標記需要人工複查。")


if __name__ == "__main__":
    prompt = " ".join(sys.argv[1:]) or (
        "請幫我企劃一支 20 秒的 YouTube Shorts 短影音，主題是"
        "『同一份規格，兩套雲端：用 Microsoft Agent Framework 重現昨天的 ADK 導演 Agent』，"
        "要求 Cyberpunk 科技感、快節奏運鏡剪輯與震撼轉場音效。"
    )
    asyncio.run(main(prompt))
