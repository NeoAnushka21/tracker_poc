# OmniAI

OmniAI is a chat-based calorie and macro tracker (working name). Its chat assistant is **MacBro** (macro + bro). You describe what you ate in plain language. LLM estimates the nutrition and proposes a log entry, and **nothing is saved until you click Confirm**.

Spec: [macro_tracker_build_spec (1).md](macro_tracker_build_spec%20(1).md).

## Documentation

| Doc | For |
|---|---|
| [docs/user-guide.md](docs/user-guide.md) | User manual and walkthrough (the in-app **? Guide** tour is its short version) |
| [docs/hld.md](docs/hld.md) | High-level design with diagrams |
| [docs/technical-overview.md](docs/technical-overview.md) | Stack, API, data model, LLM layer, components |
| [docs/llm-routing-strategy.md](docs/llm-routing-strategy.md) | Multi-model open-source routing plan |
| [docs/deployment.md](docs/deployment.md) | Deploying on Render with a Neon Postgres database |

Keep these in sync with every code or UI change. See the checklist in [docs/README.md](docs/README.md).

## Run it locally

You need Python 3.12+ and Node 20+.

**1. Backend** (first time only: create the virtual environment and install dependencies)

```bash
cd backend
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt     # Windows
# .venv/bin/python -m pip install -r requirements.txt       # macOS/Linux
```

Create `backend/.env` from `backend/.env.example` and choose a model:

- **Free, open-source (default setup):** Groq running `openai/gpt-oss-120b`. Get a free key at https://console.groq.com (no card needed). Free-tier limits allow roughly 20–30 messages a day.
- **Claude:** set `LLM_PROVIDER=anthropic` and `ANTHROPIC_API_KEY`. This gives the best estimates and costs about 1–3 cents per message.
- **Any other OpenAI-compatible endpoint** (Gemini, OpenRouter, Mistral, local Ollama) works by changing `LLM_BASE_URL` and `LLM_MODEL`.

Start it:

```bash
.venv\Scripts\python -m uvicorn app.main:app --reload --port 8000
```

On Windows, if code changes aren't picked up, start it with polling: `set WATCHFILES_FORCE_POLLING=true` first (PowerShell: `$env:WATCHFILES_FORCE_POLLING="true"`).

**2. Frontend** (in a second terminal)

```bash
cd frontend
npm install
npm run dev
```

Open http://omniai.localhost:5173 (any `*.localhost` name reaches your machine; the hostname is `APP_DEV_HOST` in `frontend/src/brand.ts`). The dev server proxies `/api` to the backend on port 8000. The launcher page (the dancing-MacBro wake screen used in production) is at http://omniai.localhost:5173/launcher.html; with the backend running it opens the app straight away, and with it stopped it shows the wake screen until it's back.

**Tests**

```bash
cd backend
.venv\Scripts\python -m pytest -q
```

The tests use a fake LLM, so they don't need an API key.

## How it works

```
user message ─► FastAPI /api/chat ─► LLM (Groq gpt-oss-120b or Claude) with tools
                                        │
             ┌──────────────────────────┼─────────────────────────┐
     get_logs / get_daily_summary   propose_entry / propose_edit / propose_delete
       (read-only, confirmed data)     (creates a PendingAction; no write)
                                        │
                     proposal card in the UI: Looks good · Needs changes · Cancel
                                        │
               POST /api/actions/{id}/confirm  ◄── the only code path that writes food logs
```

- **Confirmation is enforced in code, not only in the prompt.** The LLM can only create `pending_actions`. The write happens in `services/actions.py → confirm_action`, which only runs from the Confirm button's endpoint.
- **Sanity check on estimates:** each item's calories must roughly match its macros (4/4/9 kcal per gram, ±25%, alcohol exempt). If they don't, the model is told to recalculate before any card is shown.
- **One model call per logged meal:** proposals carry the model's reply in a `note` field, so the turn ends as soon as the card is created.
- **Needs changes** lets you type a correction. Claude re-proposes the entry, and the new card replaces the old one (the old one is marked "superseded").
- Proposals left pending for 24 hours expire. Pending proposals never count toward totals.
- The dashboard reads the database directly and never goes through the LLM.
- **Personal food library (`user_foods`):** each confirmed meal teaches the app its foods. They're stored per 100 g/ml, or per piece/serving with a gram weight when known. Next time the model only has to match the food (`food_id`), and **the app scales the nutrients in code**, so the same food always gets the same numbers. A food you edit by hand in *My foods* is never overwritten by later estimates. Cancelled proposals teach nothing.
- **Recipes:** say "save this as a recipe" (or accept the assistant's offer), give the raw ingredients for the whole batch and its yield (pieces, servings and/or cooked weight), and confirm the card. Logging "3 chapatis" then uses the recipe's per-piece values. Editing a recipe changes future logs only; past entries keep their numbers.
- **Guard against false claims:** if the model says it logged or saved something without creating a card, the app sends it back once to either create the proposal or correct itself.
- Meal type is inferred from your local time: breakfast 05–10, morning snack 10–12, lunch 12–15, evening snack 15–19, dinner 19–23, and evening snack otherwise. It's overridden when you say "for breakfast".
- Targets use Mifflin-St Jeor for BMR, multiplied by an activity factor for TDEE, then adjusted for your goal. Protein is set in g/kg, fat is 25% of calories, and carbs fill the rest. All the tunable numbers are in `backend/app/config.py`.

## Screens

- **Home (default tab):** a time-of-day greeting, today's summary (calorie ring, macro bars, water), and two streaks: days in a row with a meal logged, and days in a row on target.
- **Chat:** talk to MacBro (typing or voice). Proposals appear as cards you confirm.
- **Dashboard:** today's calorie ring; protein, fiber, carbs and fat meters; calorie split; water tracker; micronutrients; five meal sections with per-meal macros.
- **Analysis:** 7, 14 or 30-day trends: calories and protein vs target, macro lines, calorie split, calories by meal, water, and a data table. All charts have hover and keyboard tooltips.
- **My foods:** your saved foods and recipes.
- **Admin console:** reached through **Admin login** on the login page, and only for `ADMIN_EMAILS`. Admin emails can't sign up or use the normal login. The admin account is created at startup from `ADMIN_INITIAL_PASSWORD` if it doesn't exist yet. The console shows users, logins and activity, with read-only access to each user's logs, foods and chat, and every view is written to an audit log.
- **Settings (⚙):** Account (email, registration date, last login, consent, and appearance), Targets, Body profile (weight, height, optional body measurements), Password, and **Delete account**, which requires your password and permanently removes all of your data.
- **? Guide:** the first-run walkthrough. It opens once for new users and can be reopened any time.
- Light, dark or system theme (in Settings → Account), with text contrast checked against WCAG AA in both.
- Sign-up requires accepting a data-use consent notice. Existing accounts are asked once, and again if the wording (`CONSENT_VERSION`) changes.

## Code map

| Path | What it does |
|---|---|
| `backend/app/models.py` | Database schema (SQLAlchemy, SQLite) |
| `backend/app/llm/tools.py` | Tool definitions + handlers the LLM can call |
| `backend/app/llm/prompt.py` | System prompt (stable, cached) + per-turn context |
| `backend/app/llm/chat.py` | One chat turn: history → tool loop → reply |
| `backend/app/llm/provider.py` | LLM providers: Claude, and any OpenAI-compatible API (Groq, Gemini, Ollama…) |
| `backend/app/services/actions.py` | Confirm / reject / expire proposals |
| `backend/app/services/logs.py` | Totals, daily summary, log queries |
| `backend/app/services/foods.py` | Food library + recipes: units, scaling, recipe maths |
| `backend/app/routers/foods.py` | My foods API (list / edit / delete) |
| `backend/app/nutrition.py` | BMR / TDEE / target calculation |
| `frontend/src/components/` | Auth, Onboarding, GuideTour, Chat (with voice input), ProposalCard, Dashboard, Analysis, My foods, Settings, Admin |

Full details: [docs/technical-overview.md](docs/technical-overview.md).

## Scope of this base version

**Included:**

- email + password login, consent, and an admin console
- onboarding with editable targets
- chat logging (typed or by voice) with clarifying questions, and confirm cards
- editing, deleting, moving and copying through chat or the dashboard
- questions about past logs
- a daily dashboard with macros, fiber, micronutrients, water and five meals
- 7, 14 and 30-day analysis
- a food library and recipes
- a body profile
- a first-run guide
- light and dark themes

**Deferred** (the schema already has room for these):

- OTP email verification
- Branded-product web search. For now Claude uses what it knows about the label and asks you for the figures if it doesn't know the product.
- A cleanup job for stale proposals (they expire lazily on the next request)

**Deployment:** open it from the always-on launcher (Render static site `omniai-app`, e.g. https://omniai-app.onrender.com), which shows a dancing-MacBro screen while the app at https://omniai-hkv2.onrender.com (free web service) wakes up, with data in Neon (free Postgres). See [docs/deployment.md](docs/deployment.md). Locally the app still uses SQLite.

**Differences from the spec's schema:**

- Proposed writes are stored in a `pending_actions` table instead of a `status=pending` column on `log_entries`. This gives proposed edits and deletes of confirmed entries somewhere to wait for confirmation too.
- `log_entries.eaten_at` (when you ate) is separate from `created_at` (when you logged it).
- Deletes are soft (`deleted_at`).
- Tables are created on startup. Add Alembic before changing the schema on a database with real data in it.
