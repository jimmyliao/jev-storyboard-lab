"""Shared structured-output schema for the storyboard demos.

Used identically by both the Google ADK demo (as `output_schema`) and the
Microsoft Agent Framework demo (as `response_format`) — the whole point of
this repo is that the schema and the Jev QC gate are vendor-neutral; only
the agent framework + model wiring differs between the two demos.
"""

from pydantic import BaseModel, Field


class StoryboardScene(BaseModel):
    scene_number: int = Field(description="分鏡編號，從 1 開始")
    duration_seconds: int = Field(description="該分鏡的預估秒數，通常介於 3 到 8 秒")
    visual_description: str = Field(
        description="極度詳細的畫面視覺描述（Prompt 級別），包含主體、光影、場景"
    )
    camera_movement: str = Field(description="運鏡指示，如：Zoom In, Pan Left, Static 等")
    voiceover: str = Field(description="旁白台詞。如果沒有旁白請留空字串")
    sound_effects: str = Field(description="音效或背景音樂指示，如：鍵盤敲擊聲、轉場音效")


class VideoStoryboard(BaseModel):
    video_title: str
    target_platform: str = Field(description="如 YouTube Shorts, TikTok 等")
    total_duration_seconds: int
    scenes: list[StoryboardScene]
