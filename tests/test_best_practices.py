#!/usr/bin/env python3
import asyncio
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.append(str(Path(__file__).resolve().parents[1]))

from core.client import AsyncTranslator
from core.config import TranslatorConfig
from server.api import DoubaoServer


@pytest.mark.asyncio
async def test_async_translate_respects_passed_languages(monkeypatch):
    config = TranslatorConfig(
        api_key="test-key",
        models=["doubao-seed-translation-250915"],
        max_concurrent=5,
        max_requests_per_second=10.0,
    )
    translator = AsyncTranslator(config)

    captured = {}

    async def fake_special_endpoint(text, source, target, model):
        captured["source"] = source
        captured["target"] = target
        return "ok", 1, 1

    monkeypatch.setattr(translator.client, "_request_special_endpoint", fake_special_endpoint)

    result = await translator.client.async_translate("hello", source="en", target="ja")

    assert result == "ok"
    assert captured == {"source": "en", "target": "ja"}
    await translator.close()


@pytest.mark.asyncio
async def test_client_uses_configured_max_concurrency():
    config = TranslatorConfig(
        api_key="test-key",
        models=["doubao-seed-translation-250915"],
        max_concurrent=12,
        max_requests_per_second=20.0,
    )
    translator = AsyncTranslator(config)

    assert translator.client.sem_fast._value == 12
    assert translator.client.sem_seed._value == 12
    await translator.close()


@pytest.mark.asyncio
async def test_translate_batch_uses_bounded_inflight_tasks(monkeypatch):
    config = TranslatorConfig(
        api_key="test-key",
        models=["doubao-seed-translation-250915"],
        max_concurrent=10,
        max_requests_per_second=10.0,
    )
    translator = AsyncTranslator(config)

    active = 0
    max_active = 0
    guard = asyncio.Lock()

    async def fake_async_translate(text, source="", target="en"):
        nonlocal active, max_active
        async with guard:
            active += 1
            max_active = max(max_active, active)
        await asyncio.sleep(0.01)
        async with guard:
            active -= 1
        return text.upper()

    monkeypatch.setattr(translator.client, "async_translate", fake_async_translate)

    payload = [f"item-{i}" for i in range(80)]
    result = await translator.translate_batch(payload, source_lang="en", target_lang="zh")

    assert len(result) == 80
    assert result[0] == "ITEM-0"
    assert max_active <= 25
    await translator.close()


@pytest.mark.asyncio
async def test_model_rpm_resolution_uses_base_name_rules():
    config = TranslatorConfig(
        api_key="test-key",
        models=["deepseek-v3-2-251201", "doubao-seed-code-preview-251028"],
        max_concurrent=5,
        max_requests_per_second=500.0,
        model_rpm_overrides={
            "deepseek-v3-2": 15000,
            "doubao-seed-code": 5000,
        },
        default_model_rpm=4000,
    )
    translator = AsyncTranslator(config)

    assert translator.client._resolve_model_rpm("deepseek-v3-2-251201") == 15000
    assert translator.client._resolve_model_rpm("doubao-seed-code-preview-251028") == 5000
    assert translator.client._resolve_model_rpm("unknown-model-260101") == 4000
    await translator.close()


@pytest.mark.asyncio
async def test_model_rps_limit_is_capped_by_global_max_rps():
    high_cap = TranslatorConfig(
        api_key="test-key",
        models=["doubao-seed-translation-250915"],
        max_concurrent=5,
        max_requests_per_second=500.0,
        model_rpm_overrides={"doubao-seed-translation": 5000},
        default_model_rpm=5000,
    )
    translator_high = AsyncTranslator(high_cap)
    assert translator_high.client._get_model_rps_limit("doubao-seed-translation-250915") == pytest.approx(5000 / 60.0)
    await translator_high.close()

    low_cap = TranslatorConfig(
        api_key="test-key",
        models=["doubao-seed-translation-250915"],
        max_concurrent=5,
        max_requests_per_second=50.0,
        model_rpm_overrides={"doubao-seed-translation": 5000},
        default_model_rpm=5000,
    )
    translator_low = AsyncTranslator(low_cap)
    assert translator_low.client._get_model_rps_limit("doubao-seed-translation-250915") == pytest.approx(50.0)
    await translator_low.close()


class _FailingTranslator:
    async def translate_batch(self, texts, source_lang=None, target_lang=None):
        return ["[TRANSLATION_FAILED]"]

    async def close(self):
        return None


def test_openai_endpoint_preserves_http_exception_status():
    config = TranslatorConfig(api_key="test-key")
    server = DoubaoServer(config)

    with TestClient(server.app) as client:
        server.translator = _FailingTranslator()
        response = client.post(
            "/v1/chat/completions",
            json={
                "model": "doubao-seed-translation-250915",
                "messages": [{"role": "user", "content": "hello"}],
                "target_language": "zh",
            },
        )

    assert response.status_code == 502
