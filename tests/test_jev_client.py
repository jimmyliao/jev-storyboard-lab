"""Live integration test against the real TypeSafe Jev API.

Skips automatically if TYPESAFE_API_KEY isn't set (e.g. local clone without
a key, or a CI job that hasn't been given the secret) rather than failing —
this repo is a teaching example, not a project that should block on a paid
external API being configured.
"""

import os

import pytest

from common.jev_client import check_scene

pytestmark = pytest.mark.skipif(
    not os.environ.get("TYPESAFE_API_KEY"),
    reason="TYPESAFE_API_KEY not set — skipping live Jev API test",
)


def test_short_matching_voiceover_not_flagged():
    result = check_scene(1, 4, "未來已來。")
    assert result["needs_review"] is False


def test_long_voiceover_crammed_into_short_duration_is_flagged():
    result = check_scene(
        2,
        3,
        "各位觀眾大家好，今天要跟大家介紹一個非常重要、影響深遠、"
        "而且徹底改變我們開發習慣的全新技術，請大家繼續往下看下去。",
    )
    assert result["needs_review"] is True
