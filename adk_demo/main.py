"""Run the ADK director agent, then QC every scene with Jev.

Requires:
  GOOGLE_API_KEY     — https://aistudio.google.com/apikey
  TYPESAFE_API_KEY   — https://console.typesafe.ai

Usage:
  uv run python -m adk_demo.main "20 秒的 YouTube Shorts，主題是 Google ADK 的 structured output"
"""

import asyncio
import sys

from google.adk.runners import InMemoryRunner

from adk_demo.director_agent import director_agent
from common.jev_client import check_scene
from common.schemas import VideoStoryboard


async def generate_storyboard(prompt: str) -> VideoStoryboard:
    runner = InMemoryRunner(agent=director_agent, app_name="jev-storyboard-lab")
    events = await runner.run_debug(prompt, quiet=True)

    for event in reversed(events):
        if not event.is_final_response():
            continue
        # ADK populates `event.output` with the schema-validated object when
        # `output_schema` is set on the Agent; fall back to parsing the raw
        # text if a future SDK version changes that surface.
        if event.output is not None:
            return VideoStoryboard.model_validate(event.output)
        text = event.content.parts[0].text
        return VideoStoryboard.model_validate_json(text)

    raise RuntimeError("Agent produced no final response")


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
        "『未來已來：Google ADK(Agent Development Kit) 帶來的革命性開發體驗』，"
        "要求 Cyberpunk 科技感、快節奏運鏡剪輯與震撼轉場音效。"
    )
    asyncio.run(main(prompt))
