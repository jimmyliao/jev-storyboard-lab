"""Thin wrapper around TypeSafe AI's official Python SDK (`typesafe-sdk`,
verified against 0.7.0) for the Jev (System One) API.

Vendor-neutral by design: this module knows nothing about ADK, Microsoft
Agent Framework, or Gemini/Azure OpenAI. Both demos call the same
`check_segment()` function as their QC gate, which is the point of the
article series — the validation layer doesn't change when you swap agent
frameworks.

Docs: https://docs.typesafe.ai/sdk/python
"""

import os

from typesafe_sdk import Noul, TypeSafeClient

MODEL = "jev-latest"


class JevError(RuntimeError):
    pass


def _client() -> TypeSafeClient:
    if not os.environ.get("TYPESAFE_API_KEY"):
        raise JevError(
            "TYPESAFE_API_KEY is not set. Get a key at https://console.typesafe.ai "
            "and export it before running the demos."
        )
    # TypeSafeClient reads TYPESAFE_API_KEY from the environment itself.
    return TypeSafeClient()


def check_segment(segment_id: str, duration_sec: float, caption: str | None) -> dict:
    """QC gate used by both demos: the Timeline schema (see schemas.py) only
    guarantees `caption` and `duration_sec` are individually well-typed —
    it says nothing about whether a caption's reading/narration length is
    plausible for the seconds allotted. This flags the mismatch so the
    caller can regenerate just that segment instead of the whole timeline.

    Returns e.g. {"needs_review": True, "confidence": 0.83}
    """
    if not caption:
        return {"needs_review": False, "confidence": 0.0}

    state = f"片段 {segment_id}：標註時長 {duration_sec} 秒，畫面文字/旁白「{caption}」"
    with _client() as client:
        try:
            response = client.system_one(
                state=state,
                questions={
                    "duration_caption_mismatch": Noul(
                        instructions=(
                            "以正常中文語速估算，讀完/唸完這段文字所需時間，"
                            "是否明顯超過或短於標註的秒數（誤差超過約 30%）？"
                        )
                    )
                },
                model=MODEL,
            )
        except Exception as e:  # typesafe_sdk raises its own exception types on 4xx/5xx
            raise JevError(f"Jev API error: {e}") from e

    answer = response.answers["duration_caption_mismatch"]
    return {"needs_review": answer.noul > 0.6, "confidence": answer.noul}
