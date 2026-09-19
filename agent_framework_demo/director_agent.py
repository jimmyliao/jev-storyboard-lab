"""Microsoft Agent Framework demo: the same storyboard agent, on Azure AI Foundry.

Verified against agent-framework==1.19.0 / agent-framework-azure-ai==1.0.0rc6
(2026-09). This is the Azure-ecosystem twin of adk_demo/director_agent.py —
same instructions, same VideoStoryboard schema (from common/schemas.py),
different framework + model provider. Structured output is requested via
`ChatOptions(response_format=VideoStoryboard)`, Azure OpenAI's JSON-schema
strict mode under the hood (requires a GPT-4o-2024-08-06+ or GPT-5.x
deployment — structured outputs aren't supported on older deployments).
"""

from agent_framework import Agent, ChatOptions
from agent_framework.foundry import FoundryChatClient

from common.schemas import VideoStoryboard

INSTRUCTIONS = (
    "你是一位專業的短影音廣告導演。請根據主題，規劃節奏緊湊、視覺衝擊力強的分鏡腳本。"
    "必須精準分配每個分鏡的秒數，確保視覺與旁白完美對齊。"
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
        default_options=ChatOptions(response_format=VideoStoryboard),
    )
