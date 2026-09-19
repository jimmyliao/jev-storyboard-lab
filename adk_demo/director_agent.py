"""Google ADK demo: an agent that plans a short-video timeline.

Verified against google-adk==2.9.2 (2026-09). Note the real field name is
`output_schema`, not `response_schema` as some older blog posts show —
`response_schema` is not a field on google.adk.agents.Agent in this
version; using it silently does nothing instead of raising, which is an
easy way to ship an agent that quietly ignores your schema.
"""

from google.adk.agents import Agent

from common.schemas import VideoTimeline

director_agent = Agent(
    name="director_agent",
    model="gemini-3.1-pro-preview",
    instruction=(
        "你是一位專業的短影音剪輯師。請根據主題，規劃一份 video timeline，"
        "由 title_card / photo / video_clip / credits 片段組成，"
        "確保每個片段的文字/旁白內容跟標註的秒數合理對齊，不要塞不下或太空洞。"
    ),
    output_schema=VideoTimeline,
)
