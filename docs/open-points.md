# Open points

> Last updated: 2026-09-30 (staging environment plan parked; Settings reorganised; country list narrowed to India; optional About you questions built; country and region in onboarding; profile question ideas logged; database hardening phase 1 done; monthly USDA food list check built; general food list built with raw/cooked questions; follow-ups logged; general food list idea logged; typo-tolerant saved-food and meal-word matching done, learning your spellings parked; Render waking page seen on the app's direct link, noted under section 4; Saved Food list, Body Profile rename, Explore tab placeholder and its recipe-collection follow-up; reward-style UI pass done, its follow-ups in section 5; Continue with Google built; phone app and open-source licence parked; standards gap review, section 8; #1 limits, #3 privacy, #5 headers and #4 sessions, #6 CI and #7 monitoring (code) and #8 password hashing and #9 forgot password (code) and #10 Alembic and #11 pinned dependencies and #12 health wording done; #13/#14 lint + a11y fixes, #15, #16, #20 done; #17, #18 need decisions).Until at least 2026-10-06 the app is used by one person (the owner), and the focus is the single-user experience, UI and features.

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
2. ~~**Daily AI allowance per user**~~ **Done 2026-09-29**: 20 AI messages a day per user (`AI_DAILY_MESSAGE_LIMIT`), resets at local midnight; fast paths, saved foods and buttons don't count. Still open: change it per user or from **Admin**, and show each user's use in Admin.
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

Separate and also free: **"Sign in with Google"** for OmniAI accounts (built 2026-09-29, see 2a).

### 2a. Sign-in options (discussed 2026-09-29; Google built, see Done)

| Item | Status | Notes |
|---|---|---|
| Email OTP (verification or passwordless) | Open, later | Needs an email-sending service (Render's free plan is believed to block SMTP, so an HTTP API such as Brevo's free tier) and ideally our own domain for deliverability; plus codes table, expiry, attempt and send limits. |
| ~~Forgot password~~ | **Built 2026-09-29** (needs the Brevo account to go live) | See Done and gap #9. |
| Disconnect Google from an account | Open | Not built: once linked, Google stays linked. Needs a password set first. |
| Link the privacy page on Google's Branding page | Open | `https://omniai-hkv2.onrender.com/privacy` now exists (after the next push); add it as the privacy policy link in Google Auth Platform → Branding. |
| Legal review of the privacy notice | Open | Written in plain language from what the app really does; not legal advice. Before a public launch, check it against the DPDP Rules (e.g. a named grievance contact, notice in other Indian languages on request, breach notification). |
| Existing accounts under 18 | Open | The age check applies at onboarding only; accounts created before 2026-09-29 aren't re-checked (today only the owner). |
| Logo on Google's sign-in screen | Open | Needs Google's light brand verification; without it Google shows the app name only. Wait for the final logo/name. |

## 3. Other parked items

| Item | Notes |
|---|---|
| Faster free backup LLM provider | NVIDIA is off in production (free tier is for prototyping only, and slow); see [llm-routing-strategy.md](llm-routing-strategy.md) |
| Phase-5 real-model evaluation | On hold; costs free-tier quota |
| Embeddings / vector search | Not needed yet. pgvector is available on Neon when saved-food matching needs it. |
| Custom domain | Paid; wait for the final app name (`brand.ts`, `APP_DOMAIN`) |
| Keep-awake pinger ("Option 1") | See 4 below |

## 4. Keep the server awake with a pinger ("Option 1", parked 2026-09-29)

The launcher (live since 2026-09-29) replaces Render's waking page with our dancing-MacBro screen, but the wait is still 30–60 s after ~15 min idle. A pinger would remove most waits.

- **How:** a free uptime service (e.g. UptimeRobot or cron-job.org) requests `https://omniai-hkv2.onrender.com/api/health` every 10 minutes, so the free web service never sleeps.
- **Why it fits:**
  - Render's free plan gives 750 instance-hours a month, enough to run all month.
  - `/api/health` doesn't touch the database, so Neon still sleeps and saves its compute hours.
- **What's left:** the wake screen only after a restart or redeploy.
- **Also fixes the direct link (seen 2026-09-30):** opening the app's own address (`omniai-hkv2.onrender.com`, e.g. from an old bookmark) after it has slept shows Render's black "SERVICE WAKING UP" page, because our code isn't running yet; only the launcher (`https://omniai-app.onrender.com`) shows MacBro. For now: bookmark and share the launcher. A pinger would make the direct link almost always fast too. Status: **parked**.
- **Caveat:** Render's docs don't mention whether keep-alive pings are allowed; it's common practice, but the policy could change.
- **Effort:** about 5 minutes (an account on the pinger site, one monitor), no code.

## 5. Feature follow-ups (discussed, not built)

| Item | Raised | Status | Notes |
|---|---|---|---|
| Mixed messages use the saved-foods shortcut for the foods it knows | 2026-09-29 | Open | Today "40g guava and 1 new food" goes wholly to the AI (the shortcut is all-or-nothing). Split it: known items from Saved Food, only the new ones to the AI. Saves quota. |
| Learn a food's grams per piece automatically | 2026-09-29 | Open | "1 apple" can't use the shortcut when the food is saved per 100 g without **g per piece**. Save the weight when the AI estimates a count (e.g. "a medium apple ≈ 180 g"). Workaround today: add **g per piece** in Saved Food → Edit. |
| Settings switch for vibrations | 2026-09-29 | Open | Vibrations (Android only) follow the device's "reduce motion" setting; there's no in-app on/off yet. |
| Horizontal swipe between Dashboard sections on phones | 2026-09-29 | Open | Suggested in the UI direction brief. Built instead: micronutrients fold into an accordion. Swiping could also move between days. |
| **Public UUIDs for entries, items, cards and foods** | 2026-09-30 | Decided against for now | Phase 1 gave users a UUID. The others keep integer ids: MacBro's context refers to entries and items by id, and UUIDs would cost tokens and model accuracy; every endpoint checks ownership. Revisit if ids ever leave a user's own session (sharing, public links). |
| **Database hardening, phase 2 (before user waves)** | 2026-09-30 | Open | (7) split `users` into identity/auth (+ `auth_identities` rows for password/Google) and profile; (8) `role` column instead of admin-by-email; (9) consent history as rows (DPDP proof); (10) CHECK constraints for enum-like strings and non-negative nutrients; (11) JSONB on Postgres. |
| **Database at scale (later)** | 2026-09-30 | Parked | Retention/archiving or partitioning for chat messages and LLM usage; Postgres row-level security on user_id; a separate analytics copy (e.g. DuckDB/Parquet exports); verify Neon free-plan backup/restore window. |
| **Staging environment (test before main)** | 2026-09-30 | Parked (owner: later) | Flow: build and test locally → push to a `staging` branch → CI → Render service `omniai-staging` (free) deploys it → owner checks the staging link → merge `staging` into `main` → production deploys. Needs: `render.yaml` staging service tied to the branch (own secrets, lower `AI_DAILY_MESSAGE_LIMIT`, e.g. 10, since the Groq quota is shared), CI also on pushes to `staging`, a visible STAGING badge, a **Neon branch `staging`** with its own compute (a copy of production data, so migrations are tested on real data first; switch to test data once other users join), docs in deployment.md. Owner steps: create the Neon branch, sync the Render Blueprint and enter `DATABASE_URL` (staging) and `LLM_API_KEY`; optionally add the staging URL to Google OAuth origins. Free (Render 750 instance-hours shared, both services sleep when idle; Neon branches free). Open decisions: branch name (`staging` suggested), copy of production vs empty data. |
| **More countries** | 2026-09-30 | Open (later) | India only for now (`config.SUPPORTED_COUNTRIES`). The data for all 249 countries is already in `app/data/countries.json`; to open another country add its code, and check what else depends on it first (units and food names, the general food list's Indian focus, consent and privacy wording, e.g. GDPR for the EU). |
| **About you: next uses** | 2026-09-30 | Open | Built (see Done). Still open: training vs rest-day targets from the training days; a pregnancy/breastfeeding calorie addition set with a professional (today: no deficit only); cuisine preference and reminder times (not asked yet: nothing would use them). |
| **Show "most eaten" in the app** | 2026-09-30 | Open | The data exists since migration 0003: logged items link to their saved food, so "times eaten" is a count by `user_food_id` (no separate counter needed). Still to build: "most eaten" sorting in Saved Food, top foods first in the Dashboard's suggestions, later "your usual lunch" one-tap chips. |
| **Live food APIs instead of the local general list** | 2026-09-30 | Decided against for generic foods; options open | Asked whether an open API would avoid a stale copy. USDA FoodData Central API is free (api.data.gov key, ~1,000 requests/hour) and CC0, but SR Legacy (our source) is frozen since 2018 and Foundation Foods changes ~twice a year, so live calls add latency, rate limits and messy search matches without fresher numbers; our value is the curation (aliases, raw/cooked, portions). (a) the monthly GitHub Actions check was built (see Done); still open: (b) Open Food Facts (free, ODbL, crowd-sourced) as a lookup for **branded packaged foods**, shown as a card to confirm, looked up rather than copied into our database. Paid/proprietary APIs (Nutritionix, Edamam, FatSecret) ruled out. |
| **Full USDA list or another open food database** | 2026-09-30 | Open (later) | The curated ~300-food list is the sample (see Done). Later: the full SR Legacy / Foundation Foods, or another openly licensed source. Needs better name matching, since USDA names are long ("Egg, whole, raw, fresh"). IFCT 2017 (Indian) is copyrighted, so not bulk-copied; Open Food Facts is ODbL (share-alike) and mostly packaged goods. |
| **Indian staples missing from the general list** | 2026-09-30 | Open | Not in SR Legacy in a usable form: paneer, poha, jaggery, ragi, sweet lime, amla, idli, dosa and cooked dishes. Options: an openly licensed Indian dataset (check the licence first), or owner-entered values. Until then Saved Food / the AI handle them. |
| **Raw/cooked for counted pieces** | 2026-09-30 | Open | "2 chicken drumsticks" (no weight) goes to the AI, which the prompt tells not to ask. Could add per-piece weights for the pairs. |
| Learn your own spellings of saved foods | 2026-09-30 | Open | After you confirm a card that read "panner" as Paneer, remember "panner" as another name for it, so it matches exactly next time (even for short names). Needs a small aliases table + migration. |
| Typo-tolerant filler words | 2026-09-30 | Open | Meal words are done (see Done). A typo in "had/ate" ("hd 2 eggs") still sends the message to the AI. |
| Glass (frosted, translucent) cards | 2026-09-29 | Open | Suggested in the UI direction brief. The **header** is now frosted glass over a mesh image (see Done); cards keep the softer solid look, because frosted glass needs content behind the cards to show through. |
| Haptics on a portion slider | 2026-09-29 | Open | The brief suggested a tick while sliding a portion; amounts are typed today, so there's no slider yet. |
| Chat side panel with today's totals on laptops | 2026-09-29 | On hold | Owner: keep Chat as it is for now. |
| Embedding-based food matching ("roti" = "chapati", typos) | 2026-09-28 | On hold | See section 3; pgvector on Neon when needed. |
| Trend line per body measurement (and weight) on the Body Profile tab | 2026-09-29 | Open | Today the tab shows the latest value and the change since the previous one; the dated history is stored, so a small chart per part is frontend-only work. |
| Body-fat category labels (e.g. athletic / average) | 2026-09-29 | Open | Only the estimate is shown now. Category tables (e.g. ACE) vary by source, sex and age, so choose one deliberately before adding. |
| Height history | 2026-09-29 | Open | Height is stored on the profile (latest only); weight and measurements keep full history. Rarely needed for adults. |
| Edit the AI estimate's numbers before adding it on the Dashboard | 2026-09-29 | Open | Add food shows the estimate with Add it / Change / Cancel; Change only lets you retype the food. Today, fix numbers after adding in Saved Food → Edit (future logs use them). |
| Several foods in one Dashboard add | 2026-09-29 | Open | Add food takes one food at a time (the AI may still split a dish into items). A multi-row form could add a whole meal. |
| Clean up Dashboard estimates left open | 2026-09-29 | Open | If the panel is left without Cancel (e.g. switching tabs), the estimate stays pending until the 24 h expiry. Harmless (hidden from the chat), but a scheduled cleanup would tidy it. |
| Align Analysis's "on target" days with the protein streak | 2026-09-29 | Open | Home's streak now only needs 85% of protein; Analysis still counts a day on target at calories ±10% and protein ≥90% (`ADHERENCE_*` in config). Change it only if the owner wants one rule everywhere. |
| Record a short error reason for failed AI calls (e.g. "invalid key", "bad request") in the admin AI usage view | 2026-09-29 | Open | On 2026-09-29 live chat failed with "servers are down" because the Groq key saved in Render was wrong. `llm_usage` only says `error`, so finding the cause needed Render's logs. A sanitised reason (HTTP status + provider message, never the key) would show it in **Admin → AI usage**. |
| **Explore: recipe collections** (High protein, Non-veg quick & easy, Healthy desserts, Vegetarian protein, Under 400 kcal, Breakfast ideas) | 2026-09-29 | Open (tab built as a placeholder) | Owner's plan: curated recipes with macros worked out, loggable in one tap. To decide: where recipes come from (hand-written, AI-drafted then checked, or open recipe data with a compatible licence), how they're stored (shared tables, not per-user `user_foods`), and whether logging goes through a confirm card like chat. More ideas will be added here. |
| Phone app (installable web app first, store apps later) and an open-source licence | 2026-09-29 | Later stage | Owner: look at this later. See section 7. |

## 6. Decided against (kept for the record)

| Idea | Decided | Why |
|---|---|---|
| Left sidebar navigation on laptops | 2026-09-29 | Owner: keep the same top tabs on phone and laptop. |
| Creating an AI key for each user automatically at sign-in | 2026-09-29 | Not possible: providers have no API to create accounts or keys for someone, and automating sign-ups breaks their terms (section 2 has the workable options). |
| Forwarding all `/api` traffic through the static launcher site | 2026-09-29 | A reported ~15 s limit on Render's forwarded requests would cut off chat replies (up to ~90 s). The launcher only checks `/api/health` and then opens the app directly. |
| Customising Render's own "waking up" page | 2026-09-29 | Render doesn't allow it; solved with the launcher instead. |
| Other free hosts (Fly.io, Koyeb, Railway, Hugging Face Spaces, Vercel for the backend) | 2026-09-29 | No longer free or unsuitable (card holds, trial credits, time limits); Render + Neon chosen. Google Cloud Run is the fallback if a card on file is acceptable. |
| Vector database now | 2026-09-29 | Deferred, not rejected: Postgres (Neon) was chosen so pgvector can be added later without a migration. |

## 7. Phone app and open-sourcing the code (parked 2026-09-29, for a later stage)

**Ways to get a phone app** (all open source):

| Option | What it is | Effort | Cost |
|---|---|---|---|
| 1. Installable web app (PWA) | The current site gets an app manifest and service worker: home-screen icon, full screen, faster loads. Same code. | Small (about one session) | $0 |
| 2. Wrap the web app with Capacitor (MIT) | Same React code as real Android/iPhone store apps, with phone features (notifications, camera, health data). | Medium | Google Play $25 once; Apple $99/year plus a Mac or build service for the iPhone app |
| 3. Rebuild natively (React Native / Flutter) | A separate mobile UI with the most native feel. | Large (every screen rewritten) | Same store fees as 2 |

**Suggested path:** 1 first (nearly free, most of the benefit); 2 when store listings or phone features are wanted (meal/water reminders, food photo or barcode, steps and weight from phone health apps); 3 only if the app outgrows the web version.

**Open-sourcing:** everything the app uses is already open source (React, FastAPI, Postgres, Capacitor, gpt-oss under Apache 2.0). The repo has **no licence yet**, which legally means "all rights reserved". Choose one before making it public:
- **MIT or Apache-2.0:** anyone may reuse it, including commercially; compatible with the Apple App Store.
- **AGPL:** anyone running a modified version as a service must publish their changes (protects against closed forks), but conflicts with the Apple App Store's terms.

Caveats: the hosting (Groq, Render, Neon) is a service, not open source, though anyone could self-host with open models. App stores and push notifications (Google/Apple services) are proprietary; a fully open Android route exists via F-Droid with open notification alternatives.

**Pros of a phone app:** one tap from the home screen makes logging a habit; reminders are the biggest boost to daily use; camera, voice and health-app data; feels more "real" to new users.
**Cons:** store fees and reviews (Apple: $99/year, a Mac, a review of every update); two platforms to maintain; stricter privacy declarations for health data; store apps need token-based login instead of the browser cookie; the free server's sleep matters more for an app (see section 4, the pinger).

**Pros of open-sourcing:** trust in how health data is handled, contributions, a public portfolio, free tooling for open projects.
**Cons:** anyone can copy or run a competing version (AGPL limits that, with the App Store trade-off); security issues are public and need prompt fixes; earning money needs a different model (e.g. a paid hosted version).

**Decisions needed when this is picked up:** (1) installable web app: yes/no; (2) public repo and which licence (MIT, Apache-2.0 or AGPL); (3) which stores, if any (Apple needs a Mac and the $99/year account).

## 8. Standards gap review (2026-09-29)

Checked against OWASP ASVS / Top 10, OWASP API Security Top 10, OWASP Top 10 for LLM apps, WCAG 2.2 AA, India's DPDP Act 2023, and common engineering practice. Ranked high to low; all fixes are free. Status: all **open**.

| # | Priority | Gap | Why it matters | Fix (free) |
|---|---|---|---|---|
| 1 | ~~Critical~~ **Done 2026-09-29** | ~~No rate limiting~~ | Daily AI allowance (20/day) and sign-in attempt limits built; see Done | Follow-ups: per-user/admin-adjustable allowance, limits shared across instances if we ever run more than one |
| 2 | Critical | **No backups we control**; restore never tested | Health data; Neon free keeps only a short restore window | Scheduled `pg_dump` (e.g. GitHub Actions cron), encrypted, stored privately; one test restore |
| 3 | ~~Critical~~ **Done 2026-09-29** | ~~Privacy (DPDP Act 2023)~~ | `/privacy` page, Download my data and the 18+ check built; see Done | Follow-ups below |
| 4 | ~~High~~ **Done 2026-09-29** | ~~Sessions can't be revoked~~ | Per-user session version in the token: password change signs out other devices, **Log out of all devices** ends all; see Done | Follow-up: a list of active devices (would need a sessions table); shorter admin sessions (#15) |
| 5 | ~~High~~ **Done 2026-09-29** | ~~No security headers; API docs public~~ | CSP, HSTS, no framing, nosniff, Referrer- and Permissions-Policy; `/docs` off in production; see Done | Follow-up: collect CSP violation reports; add `http://localhost:8000` to the Google client's origins to test Google sign-in on the built app locally |
| 6 | ~~High~~ **Done 2026-09-29** | ~~No CI~~ | GitHub Actions: tests on SQLite and Postgres, build, dependency audits; Render deploys only after they pass; see Done | Follow-up: frontend lint/tests (#14) join CI when added |
| 7 | High → **code done 2026-09-29**, accounts to create | ~~No error monitoring or uptime alerts~~ | Request ids, friendly 500 with a ref, optional private Sentry built; see Done | **Owner:** create the free Sentry and UptimeRobot accounts (steps in deployment.md), add `SENTRY_DSN` in Render. Later: browser-side error reports (needs a CSP change) |
| 8 | ~~High~~ **Done 2026-09-29** | ~~Password hashing below OWASP minimum; timing reveals emails~~ | Argon2id (19 MiB, t=2, p=1), old hashes upgraded on login, dummy check for unknown emails; see Done | – |
| 9 | High → **code done 2026-09-29**, account to create | ~~No forgot password~~ | One-time emailed link via Brevo built; see Done | **Owner:** create the free Brevo account and add `BREVO_API_KEY` and `EMAIL_FROM` in Render (deployment.md). Later: our own domain for better delivery; email OTP can reuse `services/email.py` |
| 10 | ~~Medium~~ **Done 2026-09-29** | ~~No Alembic migrations~~ | Baseline `0001`, migrations at startup, pre-Alembic databases adopted (adds the missing `google_sub` index), drift test; see Done | – |
| 11 | ~~Medium~~ **Done 2026-09-29** | ~~Dependencies not pinned~~ | `requirements.in` → pinned `requirements.txt` (uv, all platforms), Dependabot weekly PRs, audits in CI; see Done | – |
| 12 | ~~Medium~~ **Done 2026-09-29** | ~~Health-safety wording only on the Body Profile tab~~ | Notes at sign-in, Home, Dashboard; low calorie target warning; see Done | Follow-up: gentle wording if logs suggest very low intake for many days (needs care; not built) |
| 13 | Medium → **partly done 2026-09-29** | Accessibility check | Static checks (jsx-a11y via oxlint) in CI; fixed: Escape closes Settings, tab lists as proper elements, chart segments readable by screen readers, datalist labels | **Open:** automated in-browser check (axe) and a keyboard/screen-reader pass; needs the Playwright decision (see #14) |
| 14 | Medium → **partly done 2026-09-29** | Frontend lint and tests | `npm run lint` (oxlint: bugs, hooks, a11y) in CI | **Open:** Playwright end-to-end tests with a test-only fake-AI mode (owner's OK needed); work through the React Compiler warnings over time |
| 15 | ~~Medium~~ **Done 2026-09-29** | ~~Admin account password only~~ | Two-step sign-in (TOTP), 12-hour admin sessions, recovery script; see Done | **Owner:** switch it on in Admin → Two-step sign-in |
| 16 | ~~Low~~ **Done 2026-09-29** | ~~LLM hardening~~ | Tool allow-list, adversarial tests, correction routing fix, Groq retention on the privacy page; see Done | **Owner (optional):** turn on Zero Data Retention in Groq's console (Data Controls) |
| 17 | Low → **needs a decision** | **Data retention** not defined (chat and usage kept forever) | DPDP: keep data only as long as needed | Retention period + scheduled purge (e.g. chat older than 12 months) |
| 18 | Low → **proposed: accept** | Account enumeration by messages | Rate limits (#1) and the timing fix (#8) remove the easy abuse; the remaining messages ("already exists", "uses Google") help real users | Owner to confirm "accept" |
| 19 | Low | **Single instance, in-memory state** (Stop button, model cooldowns); no load test | Fine for a few users; blocks scaling | Already tracked in technical overview §11 |
| 20 | ~~Low~~ **Done 2026-09-29 (draft)** | ~~No terms of service~~ | Plain-language `/terms`; see Done | **Owner:** review the wording before a public launch |

## 9. Done (moved out of this list)

| Item | Done | Where it's documented |
|---|---|---|
| **Settings reorganised:** About you (basics + optional answers, opens first), Targets, Appearance, Account & privacy, Security, Delete account (set apart); grouped cards with label / value / action rows | 2026-09-30 | user guide §2, §15; technical overview §7; tour step 9; privacy page |
| **India only for now:** the country dropdown offers only India (pre-selected), the API refuses others; `config.SUPPORTED_COUNTRIES` | 2026-09-30 | user guide §2; technical overview §3, §7 |
| **Optional "About you" questions:** diet, allergies (+ card heads-up), pace (calorie target, 25% cap), meal times (meal guessing, Dashboard default time), training, health conditions and pregnancy/breastfeeding (explicit tick; no deficit while pregnant/breastfeeding); skippable in onboarding and for existing accounts, editable in Settings → About you; migration 0005 | 2026-09-30 | user guide §2, §15; technical overview §3, §4, §5, §7, §10; HLD §4, §5; privacy page; tour step 9 |
| **Country (required) and region (optional) in the profile:** dropdowns only (`country-region-data`, MIT; 249 countries); asked in onboarding, once for existing accounts ("Where do you live?"), editable in Settings; age shown in Settings (from the date of birth, which onboarding already required); migration 0004 | 2026-09-30 | user guide §2, §15; technical overview §2, §3, §4, §5, §10; privacy page |
| **Database hardening, phase 1 (migration 0003):** users get a public UUID (API and admin screens); logged items link to their saved food (+ general id, source; old rows linked by name); every foreign key has an ON DELETE rule, so account deletion is one delete (checked over all tables); `timestamptz` via `UTCDateTime`; composite (user_id, date/status) indexes; constraint naming convention; SQLite migrations run with FK checks off + `foreign_key_check`. Tested on SQLite and a throwaway Postgres 18 (320 passed) | 2026-09-30 | technical overview §3, §5, §10; HLD §5 |
| **Monthly USDA food list check:** GitHub Action on the 1st of each month rebuilds `general_foods.json` from USDA and reports new/removed Foundation Foods against a snapshot (baseline 394), opening one PR only when something changed; free (Actions + USDA API, optional `USDA_API_KEY`) | 2026-09-30 | deployment "Monthly USDA food list check"; technical overview §2, §10; HLD §3, §6 |
| **General food list (no AI):** ~300 common foods per 100 g from USDA FoodData Central (public domain) with our own Indian aliases and piece/cup/tbsp weights; Saved Food → general list → AI in the chat, the AI's context (`general_id`) and Dashboard Add food; confirmed foods copied into Saved Food; **raw or cooked is asked, never assumed** (39 pairs: meat, fish, rice, grains, dals), with Raw/Cooked buttons, also for saved foods named with a state | 2026-09-30 | user guide §5, §7, §9, §17; technical overview §2, §3, §4, §6, §7, §10; HLD §4.1b, §4.4, §6 |
| **Typos in saved-food names and meal words handled in plain Python (no AI):** meal words (brkfst, bekfast, bfast, lnch, dinr, mornng snak) after for/at/in/as/my/same/yesterday's; chat fast path accepts a close typo of exactly one saved food and says what it read; the AI is still shown misspelt saved foods; Dashboard asks "Did you mean …?" instead of adding a guess | 2026-09-30 | user guide §7, §9; technical overview §3, §4, §6, §7, §10; HLD §4.4 |
| **Frosted-glass header:** top bar and tabs share one header with a soft mesh-gradient image (`cover`, `center`) under 75% glass and a 12px blur, in light and dark; text contrast checked to WCAG AA; the tab underline sits above it; plain header when the device asks for reduced transparency | 2026-09-29 | technical overview §7, design brief §2 |
| **Tab changes:** Saved Food renamed **Saved Food** and turned into a list (name + calories, **Additional info** for macros, micronutrients and ingredients); Body renamed **Body Profile**; new **Explore** tab previewing recipe collections (coming soon) | 2026-09-29 | user guide §3, §9, §13, §14; technical overview §7; HLD §3 |
| **Reward-style UI pass:** neutral alabaster/charcoal backgrounds; brighter validated macro colours (green / amber / cyan); 22px corners and soft shadows; proposal cards lead with big kcal + protein, with the full table behind **View details**; spring-in for new cards; ring and bars fill with an ease-out when seen (also right after **Looks good**); moving gradient when a target is reached (protein now counts as a goal, not "over"); **MacBro thinking** animation (replaces the open "dancing MacBro while replying" item with a smaller, maths-themed version); buttons press to 98%; Dashboard micronutrients folded by default; Android vibrations for save, water and streaks | 2026-09-29 | user guide §5, §6, §11 and Home; technical overview §1/§7; design brief §3 |
| **Admin two-step sign-in** (gap review #15): authenticator-app codes (TOTP), secret stored encrypted, no code replay, 12-hour admin sessions, audited on/off, `scripts/reset_admin_2fa.py`; migration 0002. Also fixed: pre-Alembic databases are stamped at the latest revision, not the baseline | 2026-09-29 | technical overview §3/§4/§5, deployment, README |
| **AI hardening** (gap review #16): only offered tools run; adversarial tests (injection, other users' data, HTML in replies); "X was 150g" corrections reach the edit tools; privacy page states Groq's retention (none by default, up to 30 days for errors/abuse) | 2026-09-29 | technical overview §6, HLD §6, privacy page |
| **Frontend lint + accessibility fixes** (gap review #13/#14, part): oxlint with jsx-a11y and hooks rules in CI; Escape closes Settings; tab lists; chart segments; datalist labels | 2026-09-29 | technical overview §10, docs/README |
| **Terms of use** (gap review #20, draft): plain-language `/terms` | 2026-09-29 | user guide §1 |
| **Health-safety wording** (gap review #12): "estimates, not medical advice" at sign-in and at the bottom of Home and the Dashboard (links to the privacy page's health section); a heads-up (not a block) for calorie targets under 1,200 kcal (women) / 1,500 kcal (men) in onboarding and Settings | 2026-09-29 | user guide §2, technical overview §7, HLD §7 |
| **Pinned dependencies** (gap review #11): `backend/requirements.in` (what we use) compiled by uv into a fully pinned, cross-platform `requirements.txt`; Dependabot weekly PRs for pip, npm and GitHub Actions; `pip-audit`/`npm audit` in CI. `httpx` moved to runtime (Brevo emails) | 2026-09-29 | technical overview §2/§10, deployment |
| **Alembic migrations** (gap review #10): baseline `0001` of the 2026-09-29 schema, applied at startup (`app/migrate.py`); databases from before (local, Neon) are brought to the baseline, get missing indexes (e.g. `users.google_sub`) and are stamped; a test fails when models and migrations disagree | 2026-09-29 | technical overview §5, deployment, README |
| **Forgot password** (gap review #9): one-time link by email (Brevo HTTP API), 30 minutes, token hash only, token after `#` (not in logs), same reply for every email, 3 per address per hour, sign-out everywhere on reset, fixed `PUBLIC_APP_URL`; dev prints the link to the log | 2026-09-29 | user guide §1, technical overview §3/§4/§5/§7/§9, HLD §7, deployment, privacy page |
| **Password hashing** (gap review #8): Argon2id with OWASP's minimum settings (`argon2-cffi`, MIT); old scrypt hashes keep working and are replaced on each user's next login; unknown emails do the same hashing work, so login timing doesn't reveal accounts | 2026-09-29 | technical overview §1, HLD §7 |
| **Monitoring hooks** (gap review #7): `X-Request-ID` on every response and log line, unexpected errors answered with "Something went wrong (ref …)" and logged, optional Sentry reports without personal data, setup steps for Sentry and UptimeRobot (also the keep-awake pinger, section 4) | 2026-09-29 | deployment, technical overview §4/§9, HLD §7, privacy page |
| **CI** (gap review #6): GitHub Actions on every push: backend tests on SQLite and on a throwaway Postgres, frontend build, `pip-audit` and `npm audit`; Render deploys only after all pass (`autoDeployTrigger: checksPass`). Fixed a Dashboard test that failed in the evening | 2026-09-29 | deployment, technical overview §10, HLD §3.1 |
| **Revocable sessions** (gap review #4): `session_version` in every session token; a password change (or setting one) signs out other devices, and Settings → **Log out of all devices** ends every session | 2026-09-29 | user guide §15, technical overview §1/§4/§5/§7, HLD §7 |
| **Security headers** (gap review #5): Content-Security-Policy (own files + Google sign-in only, no inline scripts), HSTS over HTTPS, `X-Frame-Options`/`frame-ancestors`, `nosniff`, Referrer-Policy, Permissions-Policy, COOP for Google's popup; API docs off in production | 2026-09-29 | technical overview §4/§9, HLD §7, deployment |
| **Privacy** (gap review #3): public `/privacy` notice (what we store, why, processors, retention, rights, contact), **Download my data** in Settings, adults only (18+ and real dates checked at onboarding) | 2026-09-29 | user guide §1, §2, §15; technical overview §3/§4/§7/§9; HLD §7 |
| **Usage limits** (gap review #1): 20 AI messages per user per day, resetting at local midnight (instant replies, saved foods and buttons don't count; failed or stopped messages don't count), shown in the chat; sign-in paused after 10 wrong passwords per email in 15 min or 60 sign-in requests per address in 10 min | 2026-09-29 | user guide §5 and §17, technical overview §3/§4/§5/§9, HLD §4.1b and §7 |
| **Continue with Google** alongside email + password: open to anyone, consent for new accounts, linking to an existing email account only with the user's OK, Set password and delete-by-email for Google-only accounts | 2026-09-29 | user guide §1 and §15, technical overview §1/§4/§5/§7/§9, HLD §4.3, deployment |
| Home: **Protein streak** (≥85% of the protein target, calories ignored) replaces the Target streak | 2026-09-29 | user guide §4, technical overview §3 |
| Add food from the Dashboard without the chat: saved foods added directly, new foods estimated once by the AI and saved to Saved Food on **Add it** | 2026-09-29 | user guide §7, technical overview §3/§4/§6, HLD §4.4 |
| Deploy on Render with Neon Postgres, data copied from SQLite | 2026-09-29 | [deployment.md](deployment.md) |
| Layouts that use laptop screens (1200 px cap, multi-column pages) | 2026-09-29 | user guide "Phone or laptop", technical overview §1 |
| Own loading screen instead of Render's ("Option 2"): dancing MacBro, always-on launcher | 2026-09-29 | [deployment.md](deployment.md), user guide "Opening OmniAI" |
| Water summary card after water logs; separate macro and water tiles; Dashboard order | 2026-09-29 | user guide §6, §4, §11 |
| Micronutrients visible and editable in Saved Food | 2026-09-29 | user guide §9 |
| Fix live chat failures: nullable micronutrients in the tool schema (Groq rejected replies for saved foods), and waiting out Groq's short per-minute limits (up to 20 s) instead of "servers are down" | 2026-09-29 | technical overview §6 |
| Body tab (now Body Profile): weight, height, BMI (WHO), US Navy body-fat estimate, male/female diagram with tap-to-measure, shoulders and wrist added, edit saved entries | 2026-09-29 | user guide §14 |
| Open-source-only models, NVIDIA backup, consent wording | 2026-09-28 | [llm-routing-strategy.md](llm-routing-strategy.md) |
