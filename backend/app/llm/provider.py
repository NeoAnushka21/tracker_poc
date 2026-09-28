"""Thin LLM provider interface, so the vendor/model can be swapped later.

Messages use the Anthropic Messages shape ({"role", "content"}) as the
canonical format; another provider would translate at this boundary.
"""
import json
import re
from dataclasses import dataclass, field
from typing import Any, Protocol

import anthropic

from app.config import LLM_API_KEY, LLM_BASE_URL, LLM_EFFORT, LLM_MAX_TOKENS, LLM_MODEL, LLM_PROVIDER


class LLMError(Exception):
    """Raised when the LLM call fails in a way the user should be told about."""


class LLMRateLimited(LLMError):
    """The model's quota is used up for now; retry_after is in seconds when the host says."""

    def __init__(self, message: str, retry_after: float | None = None):
        super().__init__(message)
        self.retry_after = retry_after


_WAIT = re.compile(r"try again in\s+((?:\d+h)?(?:\d+m(?!s))?(?:[\d.]+s)?(?:[\d.]+ms)?)", re.I)


def retry_after_seconds(message: str) -> float | None:
    """Parse waits like 'Please try again in 14m16.5s' (Groq) into seconds."""
    m = _WAIT.search(message or "")
    if not m or not m.group(1):
        return None
    total = 0.0
    for num, unit in re.findall(r"([\d.]+)(ms|h|m|s)", m.group(1)):
        total += float(num) * {"h": 3600, "m": 60, "s": 1, "ms": 0.001}[unit]
    return total or None


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
    # {"prompt_tokens": int, "completion_tokens": int} when the provider reports it.
    usage: dict | None = None


class LLMProvider(Protocol):
    provider_name: str
    model: str

    def complete(
        self, *, system_stable: str, system_dynamic: str, messages: list[dict], tools: list[dict]
    ) -> LLMResponse: ...


class AnthropicProvider:
    provider_name = "anthropic"

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
            raise LLMRateLimited("The LLM is rate-limited right now. Try again in a minute.") from e
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
        u = getattr(response, "usage", None)
        return LLMResponse(
            text=text,
            tool_calls=calls,
            stop_reason=response.stop_reason,
            assistant_content=response.content,
            usage={"prompt_tokens": u.input_tokens, "completion_tokens": u.output_tokens} if u else None,
        )


class OpenAICompatibleProvider:
    """Any OpenAI-style chat-completions API: Groq, Gemini, OpenRouter, Mistral, Ollama, ...

    Translates the canonical (Anthropic-shaped) messages and tools at this boundary.
    Its assistant_content is a list of Anthropic-style dict blocks, so the chat loop
    stays provider-agnostic.
    """

    def __init__(self, model: str = LLM_MODEL, base_url: str = LLM_BASE_URL, api_key: str = LLM_API_KEY,
                 provider_name: str | None = None, max_retries: int = 1, timeout: float = 60):
        self.model = model
        self.base_url = base_url
        self.api_key = api_key
        self.provider_name = provider_name or _host_name(base_url)
        # Few retries: on a 429 the model pool fails over to another model instead of waiting.
        self.max_retries = max_retries
        self.timeout = timeout   # seconds; a hung request fails over instead of freezing the chat
        self._client = None

    @property
    def client(self):
        if self._client is None:
            import openai
            self._client = openai.OpenAI(api_key=self.api_key or "none", base_url=self.base_url,
                                         max_retries=self.max_retries, timeout=self.timeout)
        return self._client

    def complete(self, *, system_stable, system_dynamic, messages, tools) -> LLMResponse:
        import openai

        if not self.api_key and "localhost" not in self.base_url and "127.0.0.1" not in self.base_url:
            raise LLMError("No LLM API key found. Set LLM_API_KEY in backend/.env.")
        params = {
            "model": self.model,
            "max_tokens": LLM_MAX_TOKENS,
            "messages": [{"role": "system", "content": f"{system_stable}\n\n{system_dynamic}"}]
                        + to_openai_messages(messages),
            "tools": to_openai_tools(tools),
        }
        if LLM_EFFORT and "gpt-oss" in self.model:
            params["reasoning_effort"] = LLM_EFFORT
        try:
            try:
                response = self.client.chat.completions.create(**params)
            except openai.BadRequestError as e:
                # Some hosts (e.g. Groq) reject a malformed tool call outright; the model is
                # non-deterministic, so one retry usually succeeds.
                if "tool" not in _error_message(e).lower():
                    raise
                response = self.client.chat.completions.create(**params)
        except openai.AuthenticationError as e:
            raise LLMError("The LLM API key is invalid. Check LLM_API_KEY in backend/.env.") from e
        except openai.RateLimitError as e:
            msg = _error_message(e)
            wait = retry_after_seconds(msg)
            if wait is None:
                try:
                    wait = float(e.response.headers.get("retry-after"))
                except (AttributeError, TypeError, ValueError):
                    wait = None
            raise LLMRateLimited(f"Rate limited on {self.model}: {msg}", wait) from e
        except openai.BadRequestError as e:
            raise LLMError(f"The LLM rejected the request: {_error_message(e)}") from e
        except openai.APIStatusError as e:
            raise LLMError(f"The LLM service returned an error ({e.status_code}). Try again.") from e
        except openai.APIConnectionError as e:
            raise LLMError(f"Couldn't reach the LLM service at {self.base_url}.") from e

        choice = response.choices[0]
        msg = choice.message
        text = msg.content or ""
        calls = []
        for tc in msg.tool_calls or []:
            try:
                args = json.loads(tc.function.arguments or "{}")
            except json.JSONDecodeError:
                args = {"__invalid_json__": tc.function.arguments}
            calls.append(ToolCall(id=tc.id, name=tc.function.name, input=args if isinstance(args, dict) else {}))

        blocks: list[dict] = [{"type": "text", "text": text}] if text else []
        blocks += [{"type": "tool_use", "id": c.id, "name": c.name, "input": c.input} for c in calls]
        u = getattr(response, "usage", None)
        return LLMResponse(
            text=text,
            tool_calls=calls,
            stop_reason=_FINISH_REASONS.get(choice.finish_reason, "end_turn"),
            assistant_content=blocks,
            usage={"prompt_tokens": u.prompt_tokens, "completion_tokens": u.completion_tokens} if u else None,
        )


def _host_name(base_url: str) -> str:
    """'https://api.groq.com/openai/v1' -> 'groq'."""
    host = re.sub(r"^https?://", "", base_url or "").split("/")[0].split(":")[0]
    parts = [p for p in host.split(".") if p not in ("api", "www", "com", "ai", "net", "org", "io", "cloud")]
    return parts[0] if parts else (host or "local")


_FINISH_REASONS = {
    "stop": "end_turn",
    "tool_calls": "tool_use",
    "length": "max_tokens",
    "content_filter": "refusal",
}


def _error_message(e) -> str:
    body = getattr(e, "body", None)
    if isinstance(body, dict):
        err = body.get("error", body)
        if isinstance(err, dict) and err.get("message"):
            return str(err["message"])[:300]
    return str(e)[:300]


# Fields the backend fills in when missing, so hosts that validate tool calls against the
# schema (e.g. Groq) don't reject a call just because the model left one out.
_DEFAULTED_KEYS = {"note", "fiber_g", "micronutrients"}


def _is_nullable(schema: dict) -> bool:
    return any(opt.get("type") == "null" for opt in schema.get("anyOf", []))


def _relax(schema: dict) -> dict:
    """Copy of a JSON schema where nullable/defaulted properties are no longer required."""
    if not isinstance(schema, dict):
        return schema
    out = {k: v for k, v in schema.items()}
    if "properties" in out:
        props = {k: _relax(v) for k, v in out["properties"].items()}
        out["properties"] = props
        out["required"] = [
            k for k in out.get("required", [])
            if k in props and not _is_nullable(props[k]) and k not in _DEFAULTED_KEYS
        ]
    if "items" in out:
        out["items"] = _relax(out["items"])
    if "anyOf" in out:
        out["anyOf"] = [_relax(o) for o in out["anyOf"]]
    return out


def to_openai_tools(tools: list[dict]) -> list[dict]:
    return [
        {
            "type": "function",
            "function": {
                "name": t["name"],
                "description": t.get("description", ""),
                "parameters": _relax(t["input_schema"]),
            },
        }
        for t in tools
    ]


def to_openai_messages(messages: list[dict]) -> list[dict]:
    """Anthropic-shaped messages -> OpenAI chat messages.

    Handles plain-text turns, assistant turns with tool_use blocks, and user turns
    carrying tool_result blocks (which become separate role="tool" messages).
    """
    out: list[dict] = []
    for m in messages:
        content = m["content"]
        if isinstance(content, str):
            out.append({"role": m["role"], "content": content})
            continue

        if m["role"] == "assistant":
            text = "".join(b.get("text", "") for b in content if b.get("type") == "text")
            tool_calls = [
                {
                    "id": b["id"],
                    "type": "function",
                    "function": {"name": b["name"], "arguments": json.dumps(b["input"])},
                }
                for b in content if b.get("type") == "tool_use"
            ]
            msg: dict = {"role": "assistant", "content": text or None}
            if tool_calls:
                msg["tool_calls"] = tool_calls
            out.append(msg)
        else:
            texts = []
            for b in content:
                if b.get("type") == "tool_result":
                    out.append({"role": "tool", "tool_call_id": b["tool_use_id"], "content": b["content"]})
                elif b.get("type") == "text":
                    texts.append(b["text"])
            if texts:
                out.append({"role": "user", "content": "\n".join(texts)})
    return out


_provider: LLMProvider | None = None


def get_provider() -> LLMProvider:
    global _provider
    if _provider is None:
        if LLM_PROVIDER == "anthropic":
            _provider = AnthropicProvider()
        elif LLM_PROVIDER == "openai_compatible":
            _provider = OpenAICompatibleProvider()
        else:
            raise LLMError(f"Unknown LLM_PROVIDER '{LLM_PROVIDER}' in backend/.env")
    return _provider


def set_provider(provider: LLMProvider | None) -> None:
    """Used by tests to inject a fake provider."""
    global _provider
    _provider = provider
