# jev-storyboard-lab

Same Pydantic schema, two agent frameworks, one vendor-neutral QC gate.

This repo is the companion code for a short article series comparing
[Google ADK](https://google.github.io/adk-docs/) and
[Microsoft Agent Framework](https://github.com/microsoft/agent-framework)
for building a structured-output agent — and showing that
[TypeSafe AI's Jev](https://typesafe.ai) (a calibrated decision API, not an
LLM) can sit underneath either one unchanged as a scene-level QC gate.

```
common/
  schemas.py       VideoStoryboard / StoryboardScene — the one schema both demos share
  jev_client.py     Thin client for the Jev API — used identically by both demos
adk_demo/
  director_agent.py Google ADK Agent, output_schema=VideoStoryboard, gemini-3.1-pro-preview
  main.py            generate → QC every scene with Jev → print report
agent_framework_demo/
  director_agent.py Microsoft Agent Framework Agent, response_format=VideoStoryboard, Azure AI Foundry
  main.py            same generate → QC → report, same common/jev_client.py
tests/
  test_jev_client.py live tests against the real Jev API (skips if no key)
```

## Why this exists

A common blog-post pattern for "structured output" articles is a Pydantic
schema bound to `response_schema` / `response_format`, a pretty-printed
JSON result, and a `print()`. Nobody validates whether the *content* of that
JSON is actually sane — e.g. whether `voiceover` plausibly fits inside
`duration_seconds`. This repo adds that missing validation step using a
model (Jev) purpose-trained for calibrated yes/no and scoring decisions,
and structures the code so the exact same validation call works whether the
storyboard came from Gemini-via-ADK or Azure-OpenAI-via-Agent-Framework.

## Setup

```bash
uv sync
cp .env.example .env   # fill in the keys you need for the demo(s) you're running
```

You don't need all three providers to try this repo — `common/` only needs
`TYPESAFE_API_KEY` and has its own live tests:

```bash
export TYPESAFE_API_KEY=...
uv run pytest tests/ -v
```

### Run the ADK demo

```bash
export GOOGLE_API_KEY=...       # https://aistudio.google.com/apikey
export TYPESAFE_API_KEY=...
uv run python -m adk_demo.main
```

### Run the Microsoft Agent Framework demo

Needs an Azure AI Foundry project with a structured-output-capable
deployment (GPT-4o-2024-08-06+ or GPT-5.x — older deployments don't support
`response_format` with a Pydantic schema) and `az login` for auth:

```bash
az login
export AZURE_AI_PROJECT_ENDPOINT=https://your-project.cognitiveservices.azure.com
export AZURE_AI_MODEL_DEPLOYMENT_NAME=gpt-4o
export TYPESAFE_API_KEY=...
uv run python -m agent_framework_demo.main
```

## Verified against

- `google-adk` 2.9.2 — the real field is `output_schema`, not
  `response_schema`; several blog posts (including the one this repo started
  as a rebuttal to) use the wrong name, which is silently ignored instead of
  raising.
- `agent-framework` 1.19.0 + `agent-framework-azure-ai` 1.0.0rc6 (pre-release
  — install with `uv add --prerelease=allow` if you're adding it fresh).
  `FoundryChatClient` lives under `agent_framework.foundry`.
- TypeSafe Jev API — `POST https://api.typesafe.ai/v1/systemone`, see
  `common/jev_client.py`.

Both demos' `director_agent.py` imports were checked against the installed
SDKs (constructor signatures, field names) at write time. The
Gemini/Azure-OpenAI *calls themselves* haven't been run end-to-end in this
repo's CI — that needs paid API access this repo doesn't ship with — so if
you hit an SDK surface change, please open an issue.

## License

MIT
