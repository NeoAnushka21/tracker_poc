"""Quota-aware pool of open-source models, grouped into a small and a large tier.

The chat loop asks for a tier; the pool picks a healthy model (rotating so no single model's
free quota drains first), fails over on errors, and puts a model on cooldown when its host
says the quota is used up (Groq reports how long: "try again in 14m16s"). If a whole tier is
unavailable, the other tier is used as a last resort before the user sees "servers are down".
"""
import json
import logging
import time
from dataclasses import dataclass, field
from pathlib import Path

from app import config
from app.llm import usage
from app.llm.provider import (
    AnthropicProvider, LLMError, LLMProvider, LLMRateLimited, LLMResponse, OpenAICompatibleProvider,
)

log = logging.getLogger("omniai.llm.pool")
TIERS = ("small", "large")


def model_license(model: str) -> str | None:
    """Licence by model-name prefix. Restrictive families are checked anywhere in the name, so a
    'deepseek-r1-distill-llama-70b' counts as Llama-licensed, not MIT."""
    name = model.lower().split("/")[-1].split(":")[0]
    for family in ("llama", "gemma"):
        if family in name:
            return config.MODEL_LICENSES.get(family)
    for prefix, lic in config.MODEL_LICENSES.items():
        if name.startswith(prefix):
            return lic
    return None


def is_open_source(model: str) -> bool:
    return model_license(model) in config.ALLOWED_MODEL_LICENSES


@dataclass
class ModelSlot:
    provider: LLMProvider
    tier: str
    cooldown_until: float = 0.0
    failures: int = 0
    last_error: str | None = None
    calls: int = 0
    tokens: int = 0

    @property
    def label(self) -> str:
        return f"{getattr(self.provider, 'provider_name', '?')}:{getattr(self.provider, 'model', '?')}"

    def available(self, now: float) -> bool:
        return now >= self.cooldown_until

    def status(self, now: float) -> dict:
        return {
            "provider": getattr(self.provider, "provider_name", "?"),
            "model": getattr(self.provider, "model", "?"),
            "tier": self.tier,
            "license": model_license(getattr(self.provider, "model", "")),
            "available": self.available(now),
            "cooldown_seconds": max(0, round(self.cooldown_until - now)),
            "consecutive_failures": self.failures,
            "last_error": self.last_error,
            "calls_since_start": self.calls,
            "tokens_since_start": self.tokens,
        }


@dataclass
class ModelPool:
    slots: list[ModelSlot]
    _next: dict = field(default_factory=lambda: {t: 0 for t in TIERS})

    def tier_slots(self, tier: str) -> list[ModelSlot]:
        return [s for s in self.slots if s.tier == tier]

    def _order(self, tier: str) -> list[ModelSlot]:
        """This tier's models in rotation order, then the other tier as a last resort."""
        own = self.tier_slots(tier)
        if own:
            i = self._next[tier] % len(own)
            self._next[tier] = i + 1
            own = own[i:] + own[:i]
        other = [s for s in self.slots if s.tier != tier]
        return own + other

    def complete(self, tier: str, intent: str = "", escalated: bool = False, **kwargs) -> LLMResponse:
        last_error: LLMError | None = None
        tried = 0
        for slot in self._order(tier):
            now = time.monotonic()
            if not slot.available(now):
                continue
            tried += 1
            started = time.monotonic()
            record = {"provider": getattr(slot.provider, "provider_name", "?"),
                      "model": getattr(slot.provider, "model", "?"), "tier": slot.tier,
                      "intent": intent or "chat", "escalated": escalated}
            try:
                resp = slot.provider.complete(**kwargs)
            except LLMRateLimited as e:
                wait = e.retry_after or config.LLM_RATE_LIMIT_COOLDOWN_S
                slot.cooldown_until = time.monotonic() + wait
                slot.last_error = str(e)[:200]
                log.warning("%s rate limited; cooling down %.0fs", slot.label, wait)
                usage.record(**record, latency_ms=_ms(started), outcome="rate_limited",
                             prompt_tokens=None, completion_tokens=None)
                last_error = e
                continue
            except LLMError as e:
                slot.failures += 1
                slot.last_error = str(e)[:200]
                if slot.failures >= config.LLM_FAILURES_BEFORE_COOLDOWN:
                    slot.cooldown_until = time.monotonic() + config.LLM_FAILURE_COOLDOWN_S
                    slot.failures = 0
                log.warning("%s failed: %s", slot.label, e)
                usage.record(**record, latency_ms=_ms(started), outcome="error",
                             prompt_tokens=None, completion_tokens=None)
                last_error = e
                continue
            slot.failures = 0
            slot.calls += 1
            u = resp.usage or {}
            slot.tokens += (u.get("prompt_tokens") or 0) + (u.get("completion_tokens") or 0)
            usage.record(**record, latency_ms=_ms(started), outcome="ok",
                         prompt_tokens=u.get("prompt_tokens"), completion_tokens=u.get("completion_tokens"))
            return resp
        if last_error is not None:
            raise last_error
        raise LLMError("All models are cooling down" if not tried else "No model available")

    def status(self) -> list[dict]:
        now = time.monotonic()
        return [s.status(now) for s in self.slots]


def _ms(started: float) -> int:
    return round((time.monotonic() - started) * 1000)


# --- building the pool from config ---------------------------------------------

def _extra_slots() -> list[ModelSlot]:
    """Additional providers from llm_pool.json (entries whose API key isn't set are skipped)."""
    path = Path(config.LLM_POOL_FILE)
    if not path.exists():
        return []
    import os
    try:
        spec = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        log.error("Couldn't read %s: %s", path, e)
        return []
    slots = []
    for m in spec.get("models", []):
        key = os.getenv(m.get("api_key_env", ""), "")
        if m.get("api_key_env") and not key:
            continue
        slots.append(ModelSlot(OpenAICompatibleProvider(
            model=m["model"], base_url=m["base_url"], api_key=key, provider_name=m.get("provider")), m.get("tier", "large")))
    return slots


def build_pool() -> ModelPool:
    if config.LLM_PROVIDER == "anthropic":
        slots = [ModelSlot(AnthropicProvider(m), t) for t, models in
                 (("small", config.LLM_SMALL_MODELS), ("large", config.LLM_LARGE_MODELS)) for m in models]
    elif config.LLM_PROVIDER == "openai_compatible":
        slots = [ModelSlot(OpenAICompatibleProvider(model=m), t) for t, models in
                 (("small", config.LLM_SMALL_MODELS), ("large", config.LLM_LARGE_MODELS)) for m in models]
        slots += _extra_slots()
        # Open source only (the Anthropic path is an explicit opt-in and isn't filtered).
        dropped = [s.label for s in slots if not is_open_source(s.provider.model)]
        if dropped:
            log.warning("Skipping models without an allowed open-source licence: %s", ", ".join(dropped))
        slots = [s for s in slots if is_open_source(s.provider.model)]
    else:
        raise LLMError(f"Unknown LLM_PROVIDER '{config.LLM_PROVIDER}' in backend/.env")
    # The same model listed in both tiers is kept once per tier; that's fine (one quota, two roles).
    if not slots:
        raise LLMError("No usable models configured (check LLM_SMALL_MODELS / LLM_LARGE_MODELS and licences).")
    return ModelPool(slots)


_pool: ModelPool | None = None
_pool_source: str | None = None    # "config", "override" (wraps set_provider's fake) or "explicit"


def get_pool() -> ModelPool:
    """The shared pool. Tests that call provider.set_provider(fake) get a two-tier pool around
    that one fake; tests that call set_pool() get exactly the pool they installed."""
    global _pool, _pool_source
    from app.llm import provider as provider_module
    if _pool_source == "explicit" and _pool is not None:
        return _pool
    override = provider_module._provider
    if override is not None:
        if _pool_source != "override" or _pool is None or _pool.slots[0].provider is not override:
            _pool = ModelPool([ModelSlot(override, "small"), ModelSlot(override, "large")])
            _pool_source = "override"
        return _pool
    if _pool is None or _pool_source != "config":
        _pool = build_pool()
        _pool_source = "config"
    return _pool


def set_pool(pool: ModelPool | None) -> None:
    """Tests: install a pool of fake providers (None resets to the configured one)."""
    global _pool, _pool_source
    _pool = pool
    _pool_source = "explicit" if pool is not None else None
