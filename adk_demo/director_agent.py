"""Google ADK demo: an agent that plans a short-video storyboard.

Verified against google-adk==2.9.2 (2026-09). Note the real field name is
`output_schema`, not `response_schema` as some older blog posts show —
`response_schema` is not a field on google.adk.agents.Agent in this
version; using it silently does nothing instead of raising, which is an
easy way to ship an agent that quietly ignores your schema.
"""

from google.adk.agents import Agent

from common.schemas import VideoStoryboard

director_agent = Agent(
    name="director_agent",
    model="gemini-3.1-pro-preview",
    instruction=(
        "你是一位專業的短影音廣告導演。請根據主題，規劃節奏緊湊、視覺衝擊力強的分鏡腳本。"
        "必須精準分配每個分鏡的秒數，確保視覺與旁白完美對齊。"
    ),
    output_schema=VideoStoryboard,
)
