"""Microsoft Agent Framework demo: the same timeline agent, on Azure AI Foundry.

Verified against agent-framework==1.19.0 / agent-framework-azure-ai==1.0.0rc6
(2026-09). This is the Azure-ecosystem twin of adk_demo/director_agent.py —
same instructions, same VideoTimeline schema (from common/schemas.py),
different framework + model provider. Structured output is requested via
`ChatOptions(response_format=VideoTimeline)`, Azure OpenAI's JSON-schema
strict mode under the hood (requires a GPT-4o-2024-08-06+ or GPT-5.x
deployment — structured outputs aren't supported on older deployments).
"""

from agent_framework import Agent, ChatOptions
from agent_framework.foundry import FoundryChatClient

from common.schemas import VideoTimeline

INSTRUCTIONS = (
    "你是一位專業的短影音剪輯師。請根據主題，規劃一份 video timeline，"
    "由 title_card / photo / video_clip / credits 片段組成，"
    "確保每個片段的文字/旁白內容跟標註的秒數合理對齊，不要塞不下或太空洞。"
)


def build_director_agent() -> Agent:
    """Factory instead of a module-level instance: FoundryChatClient reads
    AZURE credentials at construction time, so building it eagerly at import
    time (like the ADK demo does) would make `import agent_framework_demo`
    fail for anyone who hasn't configured Azure yet, including CI linting.
    """
    client = FoundryChatClient(
        project_endpoint=None,  # picked up from AZURE_AI_PROJECT_ENDPOINT env var
        model=None,  # picked up from AZURE_AI_MODEL_DEPLOYMENT_NAME env var
    )
    return Agent(
        client=client,
        instructions=INSTRUCTIONS,
        name="director_agent",
        default_options=ChatOptions(response_format=VideoTimeline),
    )
