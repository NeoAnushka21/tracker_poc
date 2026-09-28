# OmniAI: multi-model LLM strategy on free, open-weight models

Status: proposal · Date: 2026-09-28

## 1. Constraints

- **Open-weight models only.** No closed models (Gemini, GPT, Claude) in the default path.
- **$0: no credits purchased, no card on file.** Only standing free tiers and our own hardware.
- **Development and tests never call real APIs.** The automated tests use a fake model. Real calls are reserved for users and for one budgeted evaluation run (section 8).
- **When every model is unavailable,** users see *"MacBro's servers are temporarily down. Please try again in a little while."* The real reason goes to the server log. (Implemented.)

A note on terms: gpt-oss (Apache 2.0), Qwen (Apache 2.0) and Mistral Small (Apache 2.0) are open source. Llama uses Meta's community licence: the weights are open, but it isn't OSI open source. All of them fit "no paid closed models". If strict open-source licensing matters later, prefer the Apache-licensed ones.

## 2. Why we hit the limit today

| Fact | Number |
|---|---|
| Groq free tier for `gpt-oss-120b` | ~200,000 tokens/day, 8,000 tokens/min |
| One MacBro model call today | ~4,000–4,400 tokens before any chat history (instructions ~2k + tool definitions ~2k) |
| Model calls per logged meal | usually 1; 2 for queries, corrections or when a check sends it back |
| **Resulting capacity** | **~40 model calls a day, shared by every user** |

Two things make this fixable without paying:

1. **Quotas are per model.** On Groq, each model has its own daily allowance (for example `llama-3.1-8b-instant` ~500k tokens/day and 14,400 requests/day, `gpt-oss-20b` ~200k tokens/day, `gpt-oss-120b` ~200k tokens/day). Spreading work across models multiplies free capacity.
2. **Most messages don't need the big model, and many need no model at all.** "Drank 500 ml water", "yes", "how much protein is left?" and "had 3 chapatis" (a saved recipe) can be handled by rules, the food library, or a small model.

Limits change often. Mistral withdrew its free API allowance on 2026-09-03, and reports conflict on which models Groq includes for free. **Re-check the numbers before relying on them** (sources at the end).

## 3. Architecture: four layers

```
user message
   │
   ▼
L0  Rules + food library (no LLM) ──────────────► answer / proposal card
   │ not handled
   ▼
Router: intent + complexity (rules first, tiny model only if unsure)
   │
   ├── simple ──► L1 small model  (8B–20B)   ──┐
   └── complex ─► L2 large model  (70B–120B) ──┤
                                               ▼
                         validation (schema, calorie check, units, false-claim guard)
                                               │ fails → retry once, one tier up
                                               ▼
                                     proposal card / answer
Every call goes through a provider pool with quota tracking and failover (L3).
```

### L0: no-LLM fast paths (biggest saving, best latency)

Rule-based handlers produce the same proposal cards the model would. These are good candidates:

| Message pattern | Handled by | Result |
|---|---|---|
| "drank 1 L / 2 glasses / 500 ml water" | regex (amount + unit + "water") | water card |
| "yes", "looks good", "ok" while a card is pending | rule | "Tap **Looks good** on the card" |
| "how much protein/calories left?", "today's summary" | intent keywords + DB | the existing "day so far" text |
| "had 3 chapatis", "2 eggs", "150 g chicken" where every food is in **My foods** | parse quantity + unit + name, exact or alias match on the library | entry card with numbers computed in code |
| "same breakfast as yesterday", "repeat lunch" | rule + DB | copy card |

Anything the rules aren't sure about falls through to the router. A false negative only costs a model call; a false positive is caught by the confirm card.

### Router: pick the tier

Start with rules only; they're free and deterministic:

| Signal | Tier |
|---|---|
| Question about past data ("what did I eat…", "how much…") | L1 with **only** `get_logs` / `get_daily_summary` tools |
| Move / copy / delete / "change X to Y g" on a named food | L1 with only the edit tools |
| One or two simple foods with amounts, not in the library | L1 |
| 3+ foods, a mixed dish, a named recipe to save, a branded product, a vague portion ("a sandwich", "some biscuits"), or feedback on a card | L2 |
| Long message (> ~40 words) or several meals in one message | L2 |

Only if the rules can't decide, ask the smallest model (8B) a single classification question. That's a ~300-token prompt with no tools, returning `{"intent": ..., "complexity": "simple|complex"}`.

### Escalation: let validation decide, not guesswork

The app already rejects bad output: schema errors, calories that don't match the macros, unconvertible units, and replies claiming a save without a card. Reuse that:

1. Try the chosen tier.
2. If validation fails twice on L1, redo the turn once on L2.
3. If L2 is out of quota, try the next L2 model in the pool, then show the friendly error.

This keeps L2 for the messages that actually need it.

### Send less per call (applies to every tier)

- **Only the tools the intent needs.** Tool definitions are about half of every request. A data question needs 2 tools, not 9.
- **A slimmer prompt per intent.** The recipe and micronutrient rules only go to L2 food-logging calls.
- **A trimmed `my_foods` list:** only foods whose names appear in the message, not the latest 150.
- **Shorter history** for L1 (last 4–6 messages).

Expected effect: 1.5k–2.5k tokens for most calls instead of ~4.4k. That's an estimate to confirm with the usage log (section 6).

## 4. Model pool (all open-weight, all free, no card)

| Tier | Model | Where (free) | Notes |
|---|---|---|---|
| L1 | `llama-3.1-8b-instant` | Groq | Very fast; largest free daily quota. Good for classification, queries and simple logs. |
| L1 | `gpt-oss-20b` | Groq | Better tool calling than 8B; separate 200k/day quota. |
| L2 | `gpt-oss-120b` | Groq (current default) | Best free quality so far in our tests. |
| L2 | `llama-3.3-70b` | Groq, OpenRouter `:free`, SambaNova | Backup large model. |
| L2 | `gpt-oss-120b`, Qwen, Llama 4 Scout | Cloudflare Workers AI (10k "neurons"/day free) | Second provider for failover. |
| Backup | Various | OpenRouter free models (≈20/min, 50/day without credits) | Small, but a useful last resort. |
| Dev only | Small Qwen/Llama | Ollama on a laptop | Works offline; too slow on CPU for real users. |

Provider accounts should belong to the project, and **one account per provider**. Creating extra accounts to multiply free quotas breaks the providers' terms, so we don't do it.

All of these speak the OpenAI-compatible API, so each is one `OpenAICompatibleProvider(base_url, model, key)`. That provider already exists in `backend/app/llm/provider.py`.

## 5. Quota-aware provider pool (L3)

A small `ModelPool` that the chat loop asks for "a tier-1 model" or "a tier-2 model":

- **Registry** (config, not code): provider, base URL, model, tier, key env var, known per-minute and per-day limits.
- **Live quota tracking:** read Groq's `x-ratelimit-remaining-tokens` and `x-ratelimit-reset-*` headers after each call. On a 429, mark that model as *cooling down* until the reset time in the error (Groq reports it, e.g. "try again in 14m16s").
- **Selection:** the first healthy model in the tier, rotating so no single model drains first. Skip models whose remaining budget is smaller than the estimated request size.
- **Circuit breaker:** 3 errors in a row means 5 minutes out of rotation.
- **Persistence:** an `llm_usage` table (time, provider, model, tier, intent, prompt/completion tokens, latency, outcome), so counts survive restarts and feed the admin view.

## 6. Observability

- An **admin "AI usage" panel:** calls and tokens per model today, remaining quota, cooling-down models, L0 hit rate, escalation rate, and failures shown to users as "servers down".
- These numbers decide the next tuning step (which intents to push down a tier, which prompts to slim).

## 7. Quality safeguards (already in place, and why multi-model is safe here)

- **Every write is a proposal the user confirms**, so a weaker model can't silently store wrong data.
- **Code-side validation** (calories vs macros, unit conversion, false-claim and missed-water checks) catches most small-model mistakes.
- **The food library makes numbers model-independent.** Once a food is saved, the maths is done in code, so switching models doesn't change the result for known foods.
- **One tool contract for all models.** Only the provider adapter differs.

## 8. Evaluation without burning quota

1. Write **~60 labelled test messages** covering Indian meals, water, moves and copies, queries, ambiguous portions, recipes and branded items. Give each an expected intent and approximate macros.
2. Run the set **once per candidate model** (budget ~250k tokens, spread across models and days). Score:
   - valid tool call
   - correct intent
   - asked a question when it should have
   - kcal and protein within ±15% of the reference
3. Record every response as a fixture ("cassette"). Regression tests **replay fixtures**, so they need no API at all.
4. Adjust the routing table from the scores, e.g. move "simple logs" to 8B only if it scores within a few points of 20B.

## 9. Capacity estimate (to validate with real usage)

These are assumptions, not measurements:
- ~2k tokens per call after slimming
- ~1.3 calls per message
- 30% of messages handled by L0

| Pool | Free tokens/day | ≈ user messages/day |
|---|---|---|
| Today (gpt-oss-120b only, unslimmed) | 200k | ~30–40 |
| Groq: 8B + 20B + 120B + 70B | ~1.0M | ~550 |
| + Cloudflare / SambaNova / OpenRouter fallbacks | varies | more headroom for bursts |

That's comfortably enough for you plus a small group of test users, at $0.

## 10. Implementation plan

| Phase | Work | Main files |
|---|---|---|
| **1. Cut tokens (no new providers)** | Tool subsetting per intent, slimmer prompts, library filtered to foods named in the message, `llm_usage` logging | `llm/chat.py`, `llm/prompt.py`, `llm/tools.py`, new `models.LlmUsage` |
| **2. L0 fast paths** | Water, "yes" nudge, today-summary query, library-only logging, "same as yesterday" | new `llm/fastpath.py` (before the tool loop) |
| **3. Router + multi-model on Groq** | Rules-based intent/tier, `ModelPool` with quota tracking and cooldowns, escalation on validation failure | new `llm/router.py`, `llm/pool.py`, config registry |
| **4. Second provider + failover** | Add Cloudflare Workers AI or SambaNova to the pool | config + env keys only |
| **5. Evaluation + admin usage panel** | Labelled set, one budgeted run, cassettes, AI-usage tab | `evals/`, `routers/admin.py`, `AdminPage.tsx` |

Phases 1 and 2 alone should roughly double or triple daily capacity with no new providers. Every phase is testable with the fake model; only the phase-5 evaluation spends real quota, once.

## 11. Risks

- **Free tiers change without notice** (see Mistral). The pool makes this survivable: drop a model from the registry and the rest carry on.
- **Data use on free tiers:** some free tiers may log prompts or use them for training. Check each provider's terms, and consider adding "processed by third-party AI providers" to the consent text.
- **Numbers vary between models.** Mitigated by the library, code-side maths and confirm cards. Watch the evaluation scores.
- **Latency:** fallbacks add delay when a model is cooling down. Rules and L1 keep most replies fast.

## Sources

- Groq free-tier limits (per model): [klymentiev.com](https://klymentiev.com/blog/groq-pricing), [tokenmix.ai](https://tokenmix.ai/blog/groq-free-tier-limits-2026), [grizzlypeaksoftware.com](https://www.grizzlypeaksoftware.com/articles/p/groq-api-free-tier-limits-in-2026-what-you-actually-get-uwysd6mb), [pricepertoken.com](https://pricepertoken.com/endpoints/groq/free)
- Free LLM API comparisons: [OpenRouter: free LLM APIs compared](https://openrouter.ai/blog/tutorials/free-llm-apis-compared/), [klymentiev.com: free LLM APIs](https://klymentiev.com/blog/free-llm-api), [freellmapi.co](https://freellmapi.co/free-llm-api)
- OpenRouter free limits: [OpenRouter docs: limits](https://openrouter.ai/docs/api_reference/limits), [klymentiev.com](https://klymentiev.com/blog/openrouter-free-tier)
- Mistral free-tier change: [agentdeals.dev](https://agentdeals.dev/vendor/mistral-ai)
- Cloudflare Workers AI free tier: [Cloudflare docs: pricing](https://developers.cloudflare.com/workers-ai/platform/pricing/)
- SambaNova free tier: [yangmao.ai](https://yangmao.ai/en/providers/sambanova/)
- Measured locally: Groq 429 on 2026-09-28, "tokens per day (TPD): Limit 200000, Used 197595, Requested 4388".
