"""Thin client for TypeSafe AI's Jev (System One) API.

Vendor-neutral by design: this module knows nothing about ADK, Microsoft
Agent Framework, or Gemini/Azure OpenAI. Both demos call the same
`check_segment()` function as their QC gate, which is the point of the
article series — the validation layer doesn't change when you swap agent
frameworks.

Docs: https://docs.typesafe.ai/api.md
"""

import os

import httpx

API_URL = "https://api.typesafe.ai/v1/systemone"
MODEL = "jev-latest"


class JevError(RuntimeError):
    pass


def _api_key() -> str:
    key = os.environ.get("TYPESAFE_API_KEY")
    if not key:
        raise JevError(
            "TYPESAFE_API_KEY is not set. Get a key at https://console.typesafe.ai "
            "and export it before running the demos."
        )
    return key


def ask(state: str, questions: dict) -> dict:
    """Raw call to the Jev /v1/systemone endpoint. Returns the parsed `answers` dict."""
    resp = httpx.post(
        API_URL,
        headers={
            "Authorization": f"Bearer {_api_key()}",
            "Content-Type": "application/json",
        },
        json={"state": state, "model": MODEL, "questions": questions},
        timeout=30.0,
    )
    if resp.status_code != 200:
        raise JevError(f"Jev API error {resp.status_code}: {resp.text}")
    return resp.json()["answers"]


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
    answers = ask(
        state,
        {
            "duration_caption_mismatch": {
                "type": "noul",
                "instructions": (
                    "以正常中文語速估算，讀完/唸完這段文字所需時間，"
                    "是否明顯超過或短於標註的秒數（誤差超過約 30%）？"
                ),
            }
        },
    )
    answer = answers["duration_caption_mismatch"]
    return {"needs_review": answer["noul"] > 0.6, "confidence": answer["noul"]}
