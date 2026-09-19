"""Run the ADK director agent, then QC every segment with Jev.

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
from common.jev_client import check_segment
from common.schemas import VideoTimeline


async def generate_timeline(prompt: str) -> VideoTimeline:
    runner = InMemoryRunner(agent=director_agent, app_name="jev-storyboard-lab")
    events = await runner.run_debug(prompt, quiet=True)

    for event in reversed(events):
        if not event.is_final_response():
            continue
        # ADK populates `event.output` with the schema-validated object when
        # `output_schema` is set on the Agent; fall back to parsing the raw
        # text if a future SDK version changes that surface.
        if event.output is not None:
            return VideoTimeline.model_validate(event.output)
        text = event.content.parts[0].text
        return VideoTimeline.model_validate_json(text)

    raise RuntimeError("Agent produced no final response")


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
        "『未來已來：Google ADK(Agent Development Kit) 帶來的革命性開發體驗』，"
        "要求 Cyberpunk 科技感。"
    )
    asyncio.run(main(prompt))
