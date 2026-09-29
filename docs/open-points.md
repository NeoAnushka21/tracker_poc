# Open points

> Last updated: 2026-09-29 (wait-instead-of-failing done).Until at least 2026-10-06 the app is used by one person (the owner), and the focus is the single-user experience, UI and features.

**How this doc works (standing rule, 2026-09-29):** every idea, option or follow-up that comes up in a discussion but isn't built goes here, in the same change as the discussion's work, so nothing gets lost. Each item is either **open** (may be built later), **on hold**, or **decided against** (kept with the reason, so it isn't re-discussed from scratch). When an item is built, it moves to **Done** at the bottom with the date, and the feature itself is documented in the relevant doc.

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
3. ~~**Wait instead of failing**~~ **Done 2026-09-29** for solo use: the server now waits out short rate limits (see Done). Still open: a visible "MacBro is busy…" hint while it waits.
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
| Keep-awake pinger ("Option 1") | See 4 below |

## 4. Keep the server awake with a pinger ("Option 1", parked 2026-09-29)

The launcher (live since 2026-09-29) replaces Render's waking page with our dancing-MacBro screen, but the wait is still 30–60 s after ~15 min idle. A pinger would remove most waits.

- **How:** a free uptime service (e.g. UptimeRobot or cron-job.org) requests `https://omniai-hkv2.onrender.com/api/health` every 10 minutes, so the free web service never sleeps.
- **Why it fits:**
  - Render's free plan gives 750 instance-hours a month, enough to run all month.
  - `/api/health` doesn't touch the database, so Neon still sleeps and saves its compute hours.
- **What's left:** the wake screen only after a restart or redeploy.
- **Caveat:** Render's docs don't mention whether keep-alive pings are allowed; it's common practice, but the policy could change.
- **Effort:** about 5 minutes (an account on the pinger site, one monitor), no code.

## 5. Feature follow-ups (discussed, not built)

| Item | Raised | Status | Notes |
|---|---|---|---|
| Mixed messages use the saved-foods shortcut for the foods it knows | 2026-09-29 | Open | Today "40g guava and 1 new food" goes wholly to the AI (the shortcut is all-or-nothing). Split it: known items from My foods, only the new ones to the AI. Saves quota. |
| Learn a food's grams per piece automatically | 2026-09-29 | Open | "1 apple" can't use the shortcut when the food is saved per 100 g without **g per piece**. Save the weight when the AI estimates a count (e.g. "a medium apple ≈ 180 g"). Workaround today: add **g per piece** in My foods → Edit. |
| Dancing MacBro while MacBro is replying in Chat | 2026-09-29 | Open | Reuse the wake-screen animation (small) instead of the "thinking" dots. |
| Chat side panel with today's totals on laptops | 2026-09-29 | On hold | Owner: keep Chat as it is for now. |
| Embedding-based food matching ("roti" = "chapati", typos) | 2026-09-28 | On hold | See section 3; pgvector on Neon when needed. |
| Trend line per body measurement (and weight) on the Body tab | 2026-09-29 | Open | Today the tab shows the latest value and the change since the previous one; the dated history is stored, so a small chart per part is frontend-only work. |
| Body-fat category labels (e.g. athletic / average) | 2026-09-29 | Open | Only the estimate is shown now. Category tables (e.g. ACE) vary by source, sex and age, so choose one deliberately before adding. |
| Height history | 2026-09-29 | Open | Height is stored on the profile (latest only); weight and measurements keep full history. Rarely needed for adults. |
| Record a short error reason for failed AI calls (e.g. "invalid key", "bad request") in the admin AI usage view | 2026-09-29 | Open | On 2026-09-29 live chat failed with "servers are down" because the Groq key saved in Render was wrong. `llm_usage` only says `error`, so finding the cause needed Render's logs. A sanitised reason (HTTP status + provider message, never the key) would show it in **Admin → AI usage**. |

## 6. Decided against (kept for the record)

| Idea | Decided | Why |
|---|---|---|
| Left sidebar navigation on laptops | 2026-09-29 | Owner: keep the same top tabs on phone and laptop. |
| Creating an AI key for each user automatically at sign-in | 2026-09-29 | Not possible: providers have no API to create accounts or keys for someone, and automating sign-ups breaks their terms (section 2 has the workable options). |
| Forwarding all `/api` traffic through the static launcher site | 2026-09-29 | A reported ~15 s limit on Render's forwarded requests would cut off chat replies (up to ~90 s). The launcher only checks `/api/health` and then opens the app directly. |
| Customising Render's own "waking up" page | 2026-09-29 | Render doesn't allow it; solved with the launcher instead. |
| Other free hosts (Fly.io, Koyeb, Railway, Hugging Face Spaces, Vercel for the backend) | 2026-09-29 | No longer free or unsuitable (card holds, trial credits, time limits); Render + Neon chosen. Google Cloud Run is the fallback if a card on file is acceptable. |
| Vector database now | 2026-09-29 | Deferred, not rejected: Postgres (Neon) was chosen so pgvector can be added later without a migration. |

## 7. Done (moved out of this list)

| Item | Done | Where it's documented |
|---|---|---|
| Deploy on Render with Neon Postgres, data copied from SQLite | 2026-09-29 | [deployment.md](deployment.md) |
| Layouts that use laptop screens (1200 px cap, multi-column pages) | 2026-09-29 | user guide "Phone or laptop", technical overview §1 |
| Own loading screen instead of Render's ("Option 2"): dancing MacBro, always-on launcher | 2026-09-29 | [deployment.md](deployment.md), user guide "Opening OmniAI" |
| Water summary card after water logs; separate macro and water tiles; Dashboard order | 2026-09-29 | user guide §6, §4, §11 |
| Micronutrients visible and editable in My foods | 2026-09-29 | user guide §9 |
| Fix live chat failures: nullable micronutrients in the tool schema (Groq rejected replies for saved foods), and waiting out Groq's short per-minute limits (up to 20 s) instead of "servers are down" | 2026-09-29 | technical overview §6 |
| Body tab: weight, height, BMI (WHO), US Navy body-fat estimate, male/female diagram with tap-to-measure, shoulders and wrist added, edit saved entries | 2026-09-29 | user guide §13 |
| Open-source-only models, NVIDIA backup, consent wording | 2026-09-28 | [llm-routing-strategy.md](llm-routing-strategy.md) |
