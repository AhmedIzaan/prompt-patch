"""One-attempt Gemini adapter and explicitly separate handwritten replay provider.

The executor owns/logs bounded retries. SDK retries, automatic continuation, and
automatic function calling are disabled so no hidden model loop is introduced.
"""

from importlib.metadata import version
from pathlib import Path
from time import perf_counter
from typing import Literal, Protocol

from google import genai
from google.genai import errors, types
import httpx
import re

from promptpatch.security import contains_credentials
from pydantic import BaseModel, ConfigDict, Field, SecretStr


CallPurpose = Literal["candidate_execution", "planner"]


class ProviderError(RuntimeError):
    def __init__(self, code, *, retryable=False, timed_out=False, http_status=None):
        if not isinstance(code, str) or not re.fullmatch(r"[a-z][a-z0-9_]{0,63}", code) or contains_credentials(code):
            code = "provider_error"
        super().__init__("Model provider operation failed: " + code)
        self.code, self.retryable, self.timed_out = code, retryable, timed_out
        self.http_status = http_status if type(http_status) is int and 400 <= http_status <= 599 else None


class ModelSettings(BaseModel):
    model_config = ConfigDict(frozen=True, strict=True, extra="forbid", allow_inf_nan=False, hide_input_in_errors=True)
    model_id: str = Field(min_length=1, max_length=128, pattern=r"^[A-Za-z0-9._/-]+$")
    temperature: float = Field(default=0.0, ge=0, le=1)
    seed: int | None = None
    max_output_tokens: int = Field(default=2048, ge=128, le=4096)
    timeout_ms: int = Field(default=20000, ge=1000, le=30000)
    max_attempts: int = Field(default=2, ge=1, le=3)


class ProviderResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    provider: Literal["gemini", "replay"]
    mode: Literal["live", "replay"]
    purpose: CallPurpose
    model_id: str
    model_version: str | None = None
    sdk_version: str | None = None
    response_id: str | None = None
    raw_text: str
    elapsed_ms: float
    usage: dict[str, int | None]
    finish_reason: str
    fixture_id: str | None = None


class Provider(Protocol):
    name: str
    mode: str

    def generate_once(self, prompt, input_text, settings: ModelSettings, *, purpose: CallPurpose,
                      response_schema: dict) -> ProviderResponse: ...


class GeminiProvider:
    name, mode = "gemini", "live"

    def __init__(self, api_key: SecretStr | None, *, client_factory=genai.Client):
        if api_key is None or not api_key.get_secret_value().strip():
            raise ProviderError("missing_api_key")
        self._key, self._client_factory = api_key, client_factory

    def generate_once(self, prompt, input_text, settings, *, purpose, response_schema):
        if purpose not in {"candidate_execution", "planner"}:
            raise ProviderError("invalid_purpose")
        started = perf_counter()
        client = None
        try:
            client = self._client_factory(
                api_key=self._key.get_secret_value(), enterprise=False, vertexai=False,
                http_options=types.HttpOptions(
                    base_url="https://generativelanguage.googleapis.com", timeout=settings.timeout_ms,
                    retry_options=types.HttpRetryOptions(attempts=1),
                    client_args={"trust_env": False, "follow_redirects": False},
                ),
            )
            response = client.models.generate_content(
                model=settings.model_id, contents=input_text,
                config=types.GenerateContentConfig(
                    system_instruction=prompt, temperature=settings.temperature, seed=settings.seed,
                    max_output_tokens=settings.max_output_tokens, candidate_count=1,
                    response_mime_type="application/json", response_json_schema=response_schema,
                    automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
                    automatic_continuation=False,
                ),
            )
            reason = (response.candidates[0].finish_reason if response.candidates else None)
            reason = reason.value if reason is not None else "UNKNOWN"
            raw_text = response.text or ""
            if reason != "STOP" or not raw_text:
                raise ProviderError("incomplete_or_blocked_response")
            if len(raw_text.encode("utf-8")) > 65536:
                raise ProviderError("response_limit")
            usage = response.usage_metadata
            result = ProviderResponse(
                provider="gemini", mode="live", purpose=purpose, model_id=settings.model_id,
                model_version=response.model_version, sdk_version=version("google-genai"),
                response_id=response.response_id, raw_text=raw_text,
                elapsed_ms=(perf_counter() - started) * 1000, finish_reason=reason,
                usage={name: getattr(usage, name, None) for name in
                       ("prompt_token_count", "candidates_token_count", "thoughts_token_count", "total_token_count")},
            )
            if contains_credentials(result.model_dump(), extra=(self._key.get_secret_value(),)):
                raise ProviderError("sensitive_output")
            return result
        except (httpx.TimeoutException, TimeoutError):
            raise ProviderError("timeout", retryable=True, timed_out=True) from None
        except httpx.RequestError:
            raise ProviderError("transport_error", retryable=True) from None
        except errors.APIError as error:
            code = error.code
            raise ProviderError("timeout" if code in {408, 504} else "quota" if code == 429 else "api_error",
                                retryable=code in {408, 429, 500, 502, 503, 504},
                                timed_out=code in {408, 504}, http_status=code) from None
        except ProviderError:
            raise
        except Exception:
            # SDK/transport exception text can contain request credentials; never persist it.
            raise ProviderError("sdk_error") from None
        finally:
            if client is not None:
                try:
                    client.close()
                except Exception:
                    raise ProviderError("client_close_error") from None


class ReplayEvent(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")
    raw_text: str | None = None
    error_code: Literal["timeout", "quota", "provider_unavailable", "invalid_request"] | None = None


class ReplayFixture(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")
    fixture_id: str
    live_inference: Literal[False]
    provenance: str
    scenarios: dict[str, list[ReplayEvent]]


class ReplayProvider:
    name, mode = "replay", "replay"

    def __init__(self, fixture_path: Path, scenario: str):
        fixture = ReplayFixture.model_validate_json(Path(fixture_path).read_text())
        if scenario not in fixture.scenarios:
            raise ProviderError("replay_scenario_missing")
        self._events = iter(fixture.scenarios[scenario])
        self.fixture_id = fixture.fixture_id + ":" + scenario
        self.calls = 0

    def generate_once(self, prompt, input_text, settings, *, purpose, response_schema):
        if purpose not in {"candidate_execution", "planner"}:
            raise ProviderError("invalid_purpose")
        self.calls += 1
        event = next(self._events, None)
        if event is None:
            raise ProviderError("replay_exhausted")
        if event.error_code:
            raise ProviderError(event.error_code, retryable=event.error_code != "invalid_request",
                                timed_out=event.error_code == "timeout")
        if event.raw_text is None:
            raise ProviderError("replay_response_missing")
        return ProviderResponse(provider="replay", mode="replay", purpose=purpose,
                                model_id=settings.model_id, raw_text=event.raw_text, elapsed_ms=0.0,
                                usage={}, finish_reason="REPLAY", fixture_id=self.fixture_id)
