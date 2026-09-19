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
  schemas.py         VideoTimeline / Segment (discriminated union) — the canonical schema
  jev_client.py       Thin client for the Jev API — used identically by both demos
adk_demo/
  director_agent.py   Google ADK Agent, output_schema=VideoTimeline, gemini-3.1-pro-preview
  main.py              generate → QC every segment with Jev → print report
agent_framework_demo/
  schemas.py           VideoTimelineAzure — same segments, no discriminator (Azure rejects oneOf)
  director_agent.py   Microsoft Agent Framework Agent, response_format=VideoTimelineAzure, Azure OpenAI
  main.py              generate → convert to common.schemas.VideoTimeline → QC → report
tests/
  test_jev_client.py  live tests against the real Jev API (skips if no key)
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

Needs an Azure OpenAI / Azure AI Foundry resource with a structured-output-
capable deployment (GPT-4o-2024-08-06+ or GPT-5.x — older deployments don't
support `response_format` with a Pydantic schema). Plain API key auth via
`agent_framework.openai.OpenAIChatClient` against the resource's
OpenAI-compatible endpoint — no `az login` / Azure AD needed:

```bash
export FOUNDRY_PROJECT_ENDPOINT=https://your-resource.services.ai.azure.com/openai/v1
export FOUNDRY_MODEL=your-deployment-name
export FOUNDRY_API_KEY=...
export TYPESAFE_API_KEY=...
uv run python -m agent_framework_demo.main
```

(`agent_framework.foundry.FoundryChatClient` is a different client this repo
doesn't use — its `credential` parameter only accepts Azure AD token
credentials, not an API key. If you only have a key-based Azure OpenAI
resource, `OpenAIChatClient` is the path that actually works.)

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
- `agent-framework` 1.19.0. Live-tested end to end against a real Azure
  OpenAI deployment via `agent_framework.openai.OpenAIChatClient` (plain API
  key against the resource's `.../openai/v1` endpoint) —
  `agent_framework.foundry.FoundryChatClient` exists too but requires Azure
  AD auth (`TokenCredential`, no plain API key support), so this repo
  doesn't use it. `agent-framework-azure-ai` was tried first and dropped —
  it's a different, incompatible package (`ImportError: cannot import name
  'BaseContextProvider'` against this core version).
- Azure/OpenAI structured outputs reject Pydantic discriminated unions:
  live 400 — `'oneOf' is not permitted`. `agent_framework_demo/schemas.py`
  defines a discriminator-free `VideoTimelineAzure` for the wire format;
  `main.py` converts the response back into the canonical
  `common.schemas.VideoTimeline` before handing it to `check_segment`.
  Gemini/ADK has no such restriction (verified in Day 1).
- TypeSafe Jev API — `POST https://api.typesafe.ai/v1/systemone`, see
  `common/jev_client.py`. Also has an official SDK, `typesafe-sdk`
  (`pip install typesafe-sdk`), which `common/jev_client.py` now uses.

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
