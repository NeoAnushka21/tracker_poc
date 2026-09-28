"""Thin LLM provider interface, so the vendor/model can be swapped later.

Messages use the Anthropic Messages shape ({"role", "content"}) as the
canonical format; another provider would translate at this boundary.
"""
from dataclasses import dataclass, field
from typing import Any, Protocol

import anthropic

from app.config import LLM_EFFORT, LLM_MAX_TOKENS, LLM_MODEL


class LLMError(Exception):
    """Raised when the LLM call fails in a way the user should be told about."""


@dataclass
class ToolCall:
    id: str
    name: str
    input: dict


@dataclass
class LLMResponse:
    text: str
    tool_calls: list[ToolCall]
    stop_reason: str
    # Provider-native assistant content, appended back verbatim within a turn
    # (keeps thinking/tool_use blocks intact for the tool loop).
    assistant_content: Any = field(repr=False, default=None)


class LLMProvider(Protocol):
    def complete(
        self, *, system_stable: str, system_dynamic: str, messages: list[dict], tools: list[dict]
    ) -> LLMResponse: ...


class AnthropicProvider:
    def __init__(self, model: str = LLM_MODEL):
        self.model = model
        self._client: anthropic.Anthropic | None = None

    @property
    def client(self) -> anthropic.Anthropic:
        if self._client is None:
            self._client = anthropic.Anthropic()
        return self._client

    def complete(self, *, system_stable, system_dynamic, messages, tools) -> LLMResponse:
        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=LLM_MAX_TOKENS,
                thinking={"type": "adaptive"},
                output_config={"effort": LLM_EFFORT},
                system=[
                    # Stable prefix (tools + rules) is cached; per-turn context comes after it.
                    {"type": "text", "text": system_stable, "cache_control": {"type": "ephemeral"}},
                    {"type": "text", "text": system_dynamic},
                ],
                tools=tools,
                messages=messages,
            )
        except anthropic.AuthenticationError as e:
            raise LLMError("The LLM API key is missing or invalid. Set ANTHROPIC_API_KEY in backend/.env.") from e
        except anthropic.RateLimitError as e:
            raise LLMError("The LLM is rate-limited right now. Try again in a minute.") from e
        except anthropic.BadRequestError as e:
            raise LLMError(f"The LLM rejected the request: {e.message}") from e
        except anthropic.APIStatusError as e:
            raise LLMError(f"The LLM service returned an error ({e.status_code}). Try again.") from e
        except anthropic.APIConnectionError as e:
            raise LLMError("Couldn't reach the LLM service. Check your internet connection.") from e
        except TypeError as e:
            # Raised by the SDK when no credentials can be resolved at all.
            raise LLMError("No LLM credentials found. Set ANTHROPIC_API_KEY in backend/.env.") from e

        text = "".join(b.text for b in response.content if b.type == "text")
        calls = [
            ToolCall(id=b.id, name=b.name, input=dict(b.input))
            for b in response.content if b.type == "tool_use"
        ]
        return LLMResponse(
            text=text,
            tool_calls=calls,
            stop_reason=response.stop_reason,
            assistant_content=response.content,
        )


_provider: LLMProvider | None = None


def get_provider() -> LLMProvider:
    global _provider
    if _provider is None:
        _provider = AnthropicProvider()
    return _provider


def set_provider(provider: LLMProvider | None) -> None:
    """Used by tests to inject a fake provider."""
    global _provider
    _provider = provider
