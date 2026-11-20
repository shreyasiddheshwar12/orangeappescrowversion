"""Thin wrapper around the Claude API for the Growth Assistant.

The key stays on the server (ANTHROPIC_API_KEY). When it is missing, `configured()`
is False and callers fall back to rules that only restate the business's own data.
"""
from __future__ import annotations

import os
from typing import Type, TypeVar

from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)
DEFAULT_MODEL = "claude-opus-5-5"


class LLMError(RuntimeError):
    pass


def configured() -> bool:
    return bool(os.environ.get("ANTHROPIC_API_KEY"))


def model_name() -> str:
    return os.environ.get("ORANGE_AI_MODEL", DEFAULT_MODEL)


_client = None


def _get_client():
    global _client
    if _client is None:
        import anthropic

        _client = anthropic.AsyncAnthropic(timeout=120.0)
    return _client


async def structured(system: str, prompt: str, schema: Type[T], *, effort: str = "medium") -> T:
    """One structured call. Returns a validated `schema` instance or raises LLMError."""
    if not configured():
        raise LLMError("AI is not configured on this server.")
    import anthropic

    try:
        response = await _get_client().beta.messages.parse(
            model=model_name(),
            max_tokens=16000,
            system=system,
            messages=[{"role": "user", "content": prompt}],
            output_format=schema,
            output_config={"effort": effort},
            # If a safety classifier declines, the API retries on a fallback model in the same call.
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",
        )
    except anthropic.RateLimitError as exc:
        raise LLMError("The AI service is busy. Try again in a minute.") from exc
    except anthropic.APIStatusError as exc:
        raise LLMError(f"The AI service returned an error ({exc.status_code}).") from exc
    except anthropic.APIConnectionError as exc:
        raise LLMError("Couldn't reach the AI service.") from exc
    if response.stop_reason == "refusal":
        raise LLMError("The AI declined this request.")
    if response.stop_reason == "max_tokens" or response.parsed_output is None:
        raise LLMError("The AI response was incomplete.")
    return response.parsed_output
