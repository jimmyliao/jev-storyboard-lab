"""Microsoft Agent Framework demo: the same timeline agent, on Azure.

Verified against agent-framework==1.19.0 (2026-09). This is the Azure-
ecosystem twin of adk_demo/director_agent.py — same instructions, same
segment types, different framework + model provider.

Uses `agent_framework.openai.OpenAIChatClient` pointed at an Azure AI
Foundry project's OpenAI-compatible endpoint (`.../openai/v1`), not
`agent_framework.foundry.FoundryChatClient`. FoundryChatClient's
`credential` parameter is typed `TokenCredential | AsyncTokenCredential`
only — it requires Azure AD auth (`az login` / a service principal), not
a plain API key. If your project only has a key-based Azure OpenAI
resource (no `az login` set up), OpenAIChatClient + api_key is the tested
path; live-verified end to end against a real `gpt-5.6`-class deployment.

Structured output is requested via `ChatOptions(response_format=
VideoTimelineAzure)` — see schemas.py for why that's a distinct type
from `common.schemas.VideoTimeline`.
"""

import os

from agent_framework import Agent, ChatOptions
from agent_framework.openai import OpenAIChatClient

from agent_framework_demo.schemas import VideoTimelineAzure

INSTRUCTIONS = (
    "你是一位專業的短影音剪輯師。請根據主題，規劃一份 video timeline，"
    "由 title_card / photo / video_clip / credits 片段組成，"
    "確保每個片段的文字/旁白內容跟標註的秒數合理對齊，不要塞不下或太空洞。"
)


def build_director_agent() -> Agent:
    """Factory instead of a module-level instance: constructing the client
    reads Azure credentials immediately, so building it eagerly at import
    time (like the ADK demo does) would make `import agent_framework_demo`
    fail for anyone who hasn't configured Azure yet, including CI linting.
    """
    client = OpenAIChatClient(
        model=os.environ.get("FOUNDRY_MODEL"),
        api_key=os.environ.get("FOUNDRY_API_KEY"),
        base_url=os.environ.get("FOUNDRY_PROJECT_ENDPOINT"),
    )
    return Agent(
        client=client,
        instructions=INSTRUCTIONS,
        name="director_agent",
        default_options=ChatOptions(response_format=VideoTimelineAzure),
    )
