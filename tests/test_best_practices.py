#!/usr/bin/env python3
import asyncio
import sys
from pathlib import Path

import pytest

sys.path.append(str(Path(__file__).resolve().parents[1]))

from core.client import AsyncDoubaoClient, AsyncTranslator
from core.config import TranslatorConfig, get_language_name, validate_language_code
from core.token_tracker import TokenTracker


def test_language_helpers_cover_known_and_unknown_codes():
    assert validate_language_code("zh") is True
    assert validate_language_code("xx-not-exist") is False
    assert get_language_name("en") == "英语"
    assert get_language_name("xx-not-exist") is None


def test_translator_config_model_property_prefers_first_model():
    cfg = TranslatorConfig(api_key="test-key", models=["m1", "m2"])
    assert cfg.model == "m1"

    empty_cfg = TranslatorConfig(api_key="test-key", models=[])
    assert empty_cfg.model == "doubao-seed-translation-250915"


def test_token_tracker_estimation_and_batch_limit(tmp_path):
    quota_file = tmp_path / "quota.json"
    tracker = TokenTracker(quota_file=str(quota_file))

    assert tracker.estimate_tokens("hello world") >= 1
    assert tracker.estimate_tokens("你好世界") >= 1

    tracker.daily_quota.remaining = 10
    # "one two three four five" -> english estimate ~= 6, batch cost multiplies by 2 => 12
    assert tracker.check_batch_limit(["one two three four five"]) == 0

    tracker.daily_quota.remaining = 100
    assert tracker.check_batch_limit(["one two three four five"]) >= 1


@pytest.mark.asyncio
async def test_client_uses_fast_and_seed_lanes():
    client = AsyncDoubaoClient(
        api_key="test-key",
        models=["doubao-seed-translation-250915", "deepseek-v3-2-251201"],
    )
    try:
        assert client._get_semaphore("doubao-seed-translation-250915") is client.sem_seed
        assert client._get_semaphore("deepseek-v3-2-251201") is client.sem_fast
        assert client._is_translation_special_model("doubao-seed-translation-250915") is True
        assert client._is_translation_special_model("deepseek-v3-2-251201") is False
    finally:
        await client.close()


@pytest.mark.asyncio
async def test_translate_batch_keeps_result_order(monkeypatch):
    translator = AsyncTranslator(
        TranslatorConfig(api_key="test-key", models=["doubao-seed-translation-250915"])
    )

    async def fake_async_translate(text, source="", target="en"):
        await asyncio.sleep(0.001)
        return f"X:{text}"

    monkeypatch.setattr(translator.client, "async_translate", fake_async_translate)

    try:
        payload = ["a", "b", "c"]
        result = await translator.translate_batch(payload, source_lang="en", target_lang="zh")
        assert result == ["X:a", "X:b", "X:c"]
    finally:
        await translator.close()
