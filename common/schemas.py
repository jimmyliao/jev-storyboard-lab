"""Shared structured-output schema for the video-timeline demos.

Modeled on a real pattern from a production AI-assisted video editor: an
LLM is only ever allowed to produce JSON that validates against `Timeline`
(a discriminated union of segment types), which becomes the single
contract between the model and the render pipeline. Product-identifying
details have been stripped — segment types and fields here are generic
video-editing vocabulary, not anything proprietary.

Used identically by both the Google ADK demo (as `output_schema`) and the
Microsoft Agent Framework demo (as `response_format`) — the schema and the
Jev QC gate are vendor-neutral; only the agent framework + model wiring
differs between the two demos.
"""

from typing import Annotated, Literal, Optional, Union

from pydantic import BaseModel, ConfigDict, Field

TransitionType = Literal["fade", "crossfade", "cut"]


class _SegmentBase(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str
    transition_in: TransitionType = "fade"


class TitleCardSegment(_SegmentBase):
    type: Literal["title_card"] = "title_card"
    duration_sec: float = Field(description="這張標題卡停留的秒數")
    caption: str = Field(description="卡片上顯示的文字")


class PhotoSegment(_SegmentBase):
    type: Literal["photo"] = "photo"
    duration_sec: float = Field(description="這張照片停留的秒數")
    caption: Optional[str] = Field(default=None, description="疊加字幕或旁白文字")


class VideoClipSegment(_SegmentBase):
    type: Literal["video_clip"] = "video_clip"
    duration_sec: float = Field(description="這段影片片段使用的秒數")
    caption: Optional[str] = Field(default=None, description="疊加字幕或旁白文字")


class CreditsSegment(_SegmentBase):
    type: Literal["credits"] = "credits"
    duration_sec: float = Field(description="工作人員名單停留的秒數")
    caption: Optional[str] = Field(default=None, description="名單文字內容")


# LLM 只被允許產生驗證得過這個 discriminated union 的 JSON —— 這是模型跟
# render pipeline 之間唯一的合約，不合法就直接被 schema 擋下來（但合法不等於合理，
# 這正是 Jev 要補的那一塊）。
Segment = Annotated[
    Union[TitleCardSegment, PhotoSegment, VideoClipSegment, CreditsSegment],
    Field(discriminator="type"),
]


class VideoTimeline(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: str
    target_platform: str = Field(description="如 YouTube Shorts, TikTok 等")
    total_duration_sec: int
    segments: list[Segment]
