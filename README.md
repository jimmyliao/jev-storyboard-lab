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
  schemas.py       VideoTimeline / Segment (discriminated union) — the one schema both demos share
  jev_client.py     Thin client for the Jev API — used identically by both demos
adk_demo/
  director_agent.py Google ADK Agent, output_schema=VideoTimeline, gemini-3.1-pro-preview
  main.py            generate → QC every segment with Jev → print report
agent_framework_demo/
  director_agent.py Microsoft Agent Framework Agent, response_format=VideoTimeline, Azure AI Foundry
  main.py            same generate → QC → report, same common/jev_client.py
tests/
  test_jev_client.py live tests against the real Jev API (skips if no key)
```

## Why this exists

A common blog-post pattern for "structured output" articles is a Pydantic
schema bound to `response_schema` / `response_format`, a pretty-printed
JSON result, and a `print()`. Nobody validates whether the *content* of that
JSON is actually sane — e.g. whether a segment's `caption` plausibly fits
inside its `duration_sec`. This repo adds that missing validation step using
a model (Jev) purpose-trained for calibrated yes/no and scoring decisions,
and structures the code so the exact same validation call works whether the
timeline came from Gemini-via-ADK or Azure-OpenAI-via-Agent-Framework.

`common/schemas.py`'s discriminated-union `Segment` type (`title_card` /
`photo` / `video_clip` / `credits`, each with its own `duration_sec`) is
adapted from a real "LLM may only emit JSON that validates against this
schema" pattern used in a production AI-assisted video editor built at
[LeapDesign.ai](https://leapdesign.ai) — the segment vocabulary is generic
video-editing terminology; nothing product- or client-identifying is
included here.

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
export FOUNDRY_PROJECT_ENDPOINT=https://your-project.cognitiveservices.azure.com
export FOUNDRY_MODEL=gpt-4o
export TYPESAFE_API_KEY=...
uv run python -m agent_framework_demo.main
```

## Verified against

- `google-adk` 2.7.0 — the real field is `output_schema`, not
  `response_schema`, which several blog posts get wrong. Setting an
  unrecognized field is silently ignored instead of raising, so this is an
  easy way to ship an agent that quietly drops its schema constraint.
  Note: 2.7.0, not the latest 2.9.2 — `agent-framework>=1.19.0` (below) has a
  transitive dependency (`agent-framework-foundry-hosting`) that genuinely
  conflicts with `google-adk==2.9.2` when both live in the same environment,
  as they do here. `uv` resolves to the highest mutually-compatible version,
  which is 2.7.0. Not a typo, not staleness — a real ceiling from sharing one
  `pyproject.toml` across both demos.
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

## Author

[Jimmy Liao](https://memo.jimmyliao.net) — Google Developer Expert (AI/ML),
Microsoft MVP (AI), Co-founder & CTO at [LeapCore](https://leapcore.tw).
Companion repo for an article series comparing structured-output agents
across Google and Microsoft's stacks.

## License

MIT
