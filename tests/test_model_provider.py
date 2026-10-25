"""Actual SDK serialization with a mocked HTTP transport: NOT live API evidence."""

import json

from google import genai
import httpx
from pydantic import SecretStr
import pytest

from promptpatch.model_provider import GeminiProvider, ModelSettings, ProviderError, ReplayProvider
from promptpatch.models import SettlementExtraction
from scripts.seed_demo import SAMPLES


RAW = '{"estimated_settlement_mm":4.5,"allowable_settlement_mm":10,"evidence":{"estimated":"The estimated settlement is 4.5 mm","allowable":"the allowable settlement is 10 mm"}}'


def mock_provider(handler):
    observed, clients = [], []

    def factory(**kwargs):
        options = kwargs["http_options"]
        assert options.retry_options.attempts == 1
        assert kwargs["vertexai"] is False and kwargs["enterprise"] is False
        observed.append(options)
        kwargs["http_options"] = options.model_copy(update={
            "client_args": {**options.client_args, "transport": httpx.MockTransport(handler)},
        })
        client = genai.Client(**kwargs)
        clients.append(client._api_client._httpx_client)  # Verify SDK-owned transport cleanup.
        return client

    return GeminiProvider(SecretStr("offline-http-mock-key"), client_factory=factory), observed, clients


def response_json(finish="STOP"):
    return {"candidates": [{"content": {"role": "model", "parts": [{"text": RAW}]}, "finishReason": finish}],
            "modelVersion": "offline-mocked-model-version", "responseId": "offline-mocked-response-id",
            "usageMetadata": {"promptTokenCount": 10, "candidatesTokenCount": 20, "totalTokenCount": 30}}


@pytest.mark.parametrize("purpose", ["candidate_execution", "planner"])
def test_sdk_request_schema_budget_purpose_and_response_metadata(purpose):
    requests = []

    def handler(request):
        requests.append(request)
        return httpx.Response(200, json=response_json())

    provider, options, clients = mock_provider(handler)
    result = provider.generate_once("Candidate prompt", "Source input", ModelSettings(model_id="offline-mock-model"),
                                    purpose=purpose, response_schema=SettlementExtraction.model_json_schema())
    assert len(requests) == 1
    assert requests[0].url.host == "generativelanguage.googleapis.com"
    body = json.loads(requests[0].content)
    config = body["generationConfig"]
    assert config["responseMimeType"] == "application/json"
    assert config["responseJsonSchema"]["type"] == "object"
    assert config["maxOutputTokens"] == 2048
    assert result.raw_text == RAW and result.purpose == purpose
    assert result.sdk_version == "2.33.0"
    assert result.model_version == "offline-mocked-model-version"
    assert result.usage["total_token_count"] == 30  # Synthetic transport numbers only.
    assert result.response_id == "offline-mocked-response-id"
    assert options[0].timeout == 20000
    assert all(client.is_closed for client in clients)


@pytest.mark.parametrize("status,retryable", [(400, False), (401, False), (429, True), (503, True)])
def test_sdk_errors_are_bounded_and_sanitized(status, retryable):
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(status, json={"error": {"code": status, "message": "unsafe-key-in-error"}})

    provider, _, clients = mock_provider(handler)
    with pytest.raises(ProviderError) as error:
        provider.generate_once("prompt", "input", ModelSettings(model_id="offline-mock-model"),
                               purpose="candidate_execution", response_schema={"type": "object"})
    assert len(calls) == 1  # SDK retries are disabled; executor owns retry accounting.
    assert error.value.retryable is retryable
    assert "unsafe-key-in-error" not in str(error.value)
    assert all(client.is_closed for client in clients)


def test_sdk_timeout_is_not_a_validation_failure():
    def handler(request):
        raise httpx.ReadTimeout("unsafe-key-in-error", request=request)

    provider, _, clients = mock_provider(handler)
    with pytest.raises(ProviderError) as error:
        provider.generate_once("prompt", "input", ModelSettings(model_id="offline-mock-model"),
                               purpose="candidate_execution", response_schema={"type": "object"})
    assert error.value.code == "timeout" and error.value.timed_out
    assert "unsafe-key-in-error" not in str(error.value)
    assert all(client.is_closed for client in clients)


def test_sdk_automatic_continuation_is_disabled():
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(200, json={**response_json("CONTINUATION"), "continuationToken": "synthetic-token"})

    provider, _, _ = mock_provider(handler)
    with pytest.raises(ProviderError) as error:
        provider.generate_once("prompt", "input", ModelSettings(model_id="offline-mock-model"),
                               purpose="candidate_execution", response_schema={"type": "object"})
    assert error.value.code == "incomplete_or_blocked_response"
    assert len(calls) == 1


def test_missing_key_fails_before_client_creation():
    with pytest.raises(ProviderError) as error:
        GeminiProvider(None)
    assert error.value.code == "missing_api_key"


def test_replay_fixture_is_labelled_and_never_invents_token_usage():
    provider = ReplayProvider(SAMPLES / "replay/module05_responses.json", "decimal_ok")
    result = provider.generate_once("ignored prompt", "ignored input", ModelSettings(model_id="replay-settlement-v1"),
                                    purpose="candidate_execution", response_schema={})
    assert result.provider == "replay" and result.mode == "replay"
    assert result.fixture_id.startswith("module05-handwritten-replay-v1:")
    assert result.sdk_version is None and result.usage == {}
