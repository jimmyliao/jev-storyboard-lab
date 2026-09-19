"""Azure-compatible wire schema for structured output.

`common.schemas.VideoTimeline` uses a Pydantic discriminated union
(`Field(discriminator="type")`) for `segments`. That's fine for Gemini/ADK
(verified in Day 1) but Azure/OpenAI's structured-output mode rejects it —
live-tested 400 from the real API:

    Invalid schema for response_format 'VideoTimeline': In
    context=('properties', 'segments', 'items'), 'oneOf' is not permitted.

Pydantic's discriminated union generates `oneOf` in the JSON Schema;
OpenAI's strict mode only accepts `anyOf`. Dropping `Field(discriminator=...)`
and using a plain `Union` produces `anyOf` instead — same segment classes,
same fields, just without the discriminator hint — and Azure accepts it
(also live-tested).

`VideoTimelineAzure` is only the wire format bound to `ChatOptions
.response_format`. Once a response comes back, `main.py` converts it to
the canonical `common.schemas.VideoTimeline` via `model_validate` + a
plain `.model_dump()` round-trip — Pydantic's discriminated-union
validator still works perfectly on the *incoming* dict; the discriminator
is only a problem for schema *generation*, not for parsing.
"""

from typing import Union

from pydantic import BaseModel, ConfigDict, Field

from common.schemas import (
    CreditsSegment,
    PhotoSegment,
    TitleCardSegment,
    VideoClipSegment,
)


class VideoTimelineAzure(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: str
    target_platform: str = Field(description="如 YouTube Shorts, TikTok 等")
    total_duration_sec: int
    segments: list[Union[TitleCardSegment, PhotoSegment, VideoClipSegment, CreditsSegment]]
