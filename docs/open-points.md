# Open points

> Last updated: 2026-09-29. Decisions discussed but **parked**. Until at least 2026-10-06 the app is used by one person (the owner), and the focus is the single-user experience, UI and features. Move an item to the relevant doc once it's decided and built.

## 1. Scaling to more users (waves of 3–5)

**Bottleneck:** the shared free Groq quota, not the server or the database.

| Resource | Free limit (published, Sep 2026) | Effect at ~5 active users |
|---|---|---|
| Render web service | 512 MB, 1 instance | Fine: requests mostly wait on the LLM |
| Neon Postgres | 0.5 GB, 100 CU-hours/month | Fine for a long time |
| Groq, per minute | gpt-oss-120b: ~8K tokens and 30 requests a minute | **Hit first.** One chat message is ~3–7K tokens, so two people in the same minute collide (today: failover to the other model, else "servers are down"). |
| Groq, per day | ~200K tokens/day per model, per **account** (extra keys don't add capacity) | ~50–60 LLM-answered messages/day in total; 5 users use ~50–75 |

Check the real numbers in **Admin → AI usage** before deciding.

**Proposed rollout plan (free, open source):**

*Before the first wave:*
1. **Invite-only sign-up:** the admin creates invite codes, so the admin controls each wave.
2. **Daily AI allowance per user** (e.g. 15 LLM messages a day, adjustable in Admin). Fast paths and dashboard actions stay unlimited.
3. **Wait instead of failing:** when Groq asks to retry within a few seconds, wait and show "MacBro is busy…" instead of the error.
4. **Keep-awake pinger** on `/api/health` (it doesn't touch the database), so new users don't wait 30–60 s.
5. **Feedback button** and **per-user usage** in Admin.

*During the waves:*

6. **Fewer tokens per message:** slimmer prompt, and more no-LLM paths (repeat a past meal, a saved recipe). Embeddings could help here once saved-food lists grow.
7. **Backups:** Neon free keeps only a short restore window. Add a scheduled `pg_dump`; where to keep it privately for free is still to be decided (health data).
8. Review usage after each wave before inviting the next.

**Decision coming around 5–8 active users:** tight daily allowances on the free tier, **or** Groq pay-as-you-go. The models stay open source; only the hosting is paid. Estimate: ~$0.001–0.002 per message, about $2–4 a month for 5 active users. Needs the owner's approval (the project rule is no paid services without asking).

**Alternatives checked (Sep 2026):**
- Cerebras: advertised as "1M tokens/day free", but now appears to be a 30-day $5 trial.
- OpenRouter free models: 50 requests a day, or 1,000 after a one-time $10 purchase.
- A CPU-only self-hosted model: too slow for our prompts.

## 2. Users' own AI keys

Automatically creating an AI key for a user when they sign in is **not possible**. Providers (Groq, NVIDIA, …) have no way for another app to create an account or key for someone, and automating sign-ups would break their terms. Two workable options:

- **A. "Connect OpenRouter" button** (OpenRouter's OAuth PKCE flow): about 3 clicks, and our app receives a key tied to the user's own account.
  - Free use is about 50 requests a day per user (~20–30 messages).
  - Few Apache/MIT free models; the candidate is Qwen3.8 27B, whose licence and logging quality still need checking.
  - Free-model providers may log prompts, depending on the user's settings.
  - Try this after a quality test.
- **B. Bring your own Groq key:** a guided screen (sign up at Groq → create key → paste → **Test** button), about 2–3 minutes once.
  - Each user gets their own ~200K tokens a day with today's models and quality.
  - Friction: copying and pasting a key.

For either option:
- keys stored encrypted, never shown again, used only for that user
- a "Disconnect" option
- fallback to the shared pool

**Recommendation:** shared pool with a daily allowance by default, plus B as an optional upgrade; A after a Qwen quality test.

Separate and also free: **"Sign in with Google"** for OmniAI accounts.

## 3. Other parked items

| Item | Notes |
|---|---|
| Faster free backup LLM provider | NVIDIA is off in production (free tier is for prototyping only, and slow); see [llm-routing-strategy.md](llm-routing-strategy.md) |
| Phase-5 real-model evaluation | On hold; costs free-tier quota |
| Embeddings / vector search | Not needed yet. pgvector is available on Neon when saved-food matching needs it. |
| Custom domain | Paid; wait for the final app name (`brand.ts`, `APP_DOMAIN`) |
| Alembic migrations | Needed before the first schema change that isn't "add a nullable column" |
| Keep-awake pinger | Also useful solo, to avoid the 30–60 s first load |
