# Tandurust

**Track your food by just saying what you ate.** Tandurust is a calorie and macro tracker you talk to. Tell its assistant, **MacBro**, "2 rotis, dal and a bowl of rice for lunch", check the card it shows you, press **Looks good**, and it's logged. It's free, including the AI.

*Tandurust* (तंदुरुस्त) means "healthy, in good shape" in Hindi and Urdu.

## Why Tandurust exists

**Tracking food works, but most people stop doing it.** In a traditional tracker, every meal means searching a database, picking the right item, choosing a serving size, and doing that again for every single food on the plate. A home-cooked Indian lunch can be five or six entries. It's tedious enough that most of us quit after a few days, and a tracker you've stopped using doesn't help.

**Tandurust is for people who want to track but find it hard to stay consistent because of all that manual entry.** You describe the meal the way you'd tell a friend, typed or spoken, and the app does the rest:

- **One sentence, whole meal.** MacBro splits it into foods, works out calories, protein, carbs, fat, fiber and micronutrients, and asks a quick question if something is unclear (for example, whether the rice was weighed raw or cooked).
- **You stay in control.** Nothing is saved until you confirm. You can fix anything in plain words ("the rice was 200 g").
- **It remembers your food.** Once you've logged something, it's saved to your own food library. Next time the same food gets exactly the same numbers, instantly, without using the AI.
- **Real labels for packaged food.** For branded products, it can fetch the actual pack label from [Open Food Facts](https://world.openfoodfacts.org) instead of guessing.
- **Built for Indian food.** Roti, dal, poha, paneer, sabzis, home recipes, Indian food names and spellings, and small typos all work.

**Other trackers with AI logging often charge for it.** Tandurust offers its chat logging **free of charge**. It runs on open-source AI models through free tiers, so each account gets a daily allowance of AI messages (currently 20 a day). Plenty of things don't count against it: foods you've saved, about 300 common foods built into the app, water, and every button.

## What it's like to use

1. **Sign up** (email and password, or Continue with Google) and answer a few profile questions. Tandurust works out your calorie, protein, carb and fat targets, and you can change them.
2. On **Home**, tap MacBro ("Want to log something? Talk to me"). A chat window opens.
3. Type or say what you ate. MacBro replies with a card: the calories and protein up front, and each item with its amount so you can check it.
4. Press **Looks good** to save it, **Needs changes** to correct it, or **Cancel**.
5. Your day updates straight away: calories left, protein, macros, water and streaks.

## What's in the app

- **Home:** a greeting, today's calories and macros at a glance, water, and two streaks: days in a row with a meal logged, and days in a row reaching your protein target.
- **Chat with MacBro:** a chat window that opens over any page, like a website's chat assistant. Type or use the mic, then minimize it to a bubble or close it. Ask about past days too ("how much protein this week?"), or edit, move or delete entries.
- **Meals:** your day in detail. A compact summary of calories, protein, fiber, carbs, fat, water and micronutrients, then a colourful card for each meal (breakfast, snacks, lunch, dinner) that you can unfold to edit items or add food without the chat. **Check your progress** at the bottom opens 7, 14 or 30-day trends.
- **Saved Food:** your personal food library in three tabs: **Generic** foods, **Branded** products (with **Check label** for the real pack values) and **My Recipes**. Add foods and recipes yourself with **+ Add**.
- **Explore** (coming soon): recipe collections with the macros worked out, and workout basics.
- **Body Profile:** weight, height, BMI, an estimated body-fat percentage, and body measurements over time.
- **Settings:** your details, optional "about you" questions (diet, allergies, meal times, training), targets, light or dark theme, password, **Download my data** and **Delete account**.
- **? Guide:** a short tour that highlights each part of the app.

## Current status and limits

- **Early stage.** Tandurust is a personal project in active development, used day to day by its owner. Expect changes.
- **Free, with a daily AI limit.** It runs on free tiers of open-source models (currently Groq), so each account gets 20 AI messages a day, resetting at midnight. Saved foods, built-in foods, water and buttons don't use them.
- **India only for now.** Sign-up asks for your country, and only India is listed at the moment.
- **Estimates, not medical advice.** Calories, nutrients and targets are estimates to help you track. The app is for adults (18+).
- **Your data:** stored in a Postgres database (Neon, Singapore). You can download or delete all of it from Settings. The privacy notice is at `/privacy` in the app.

## How it works

The AI only **proposes**; the app writes to your log only after you confirm.

```
user message ─► FastAPI /api/chat ─► LLM with tools (open-source models via Groq)
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
- **Most messages never reach the AI.** Water amounts, "yes", "what's left today?", "same breakfast as yesterday" and foods you've saved or that are on the built-in list (about 300 common foods, from USDA FoodData Central, with Indian names) are answered by rules in plain Python. That keeps replies instant and saves the free quota.
- **The same food always gets the same numbers.** Each confirmed meal teaches the app its foods (`user_foods`), stored per 100 g/ml or per piece/serving. Next time the model only has to recognise the food, and **the app scales the nutrients in code**. A food you edit by hand is never overwritten by later estimates.
- **Sanity check on estimates:** each item's calories must roughly match its macros (4/4/9 kcal per gram, ±25%, alcohol exempt). If they don't, the model is told to recalculate before any card is shown.
- **Raw or cooked is never assumed.** For rice, grains, dals and meat weighed without saying which, the app asks, because the calories differ a lot.
- **Branded foods** can be checked against their real pack label from Open Food Facts; the user picks the product and the server fetches the label itself.
- **Needs changes** lets you type a correction; the model re-proposes, and the new card replaces the old one. Proposals left pending for 24 hours expire and never count toward totals.
- **Model routing:** a small model for simple messages, a larger one when needed, with automatic fallback. Only OSI open-source (Apache-2.0 / MIT) models on free tiers are used. See [docs/llm-routing-strategy.md](docs/llm-routing-strategy.md).
- **Targets** use Mifflin-St Jeor for BMR, an activity factor for TDEE, and a goal adjustment. Protein is set in g/kg, fat is 25% of calories, carbs fill the rest. The tunable numbers are in `backend/app/config.py`.

**Stack:** React 19 + Vite (TypeScript) frontend; FastAPI + SQLAlchemy backend; Postgres in production (Neon), SQLite locally; Alembic migrations; deployed on Render; CI on GitHub Actions (tests on SQLite and Postgres, build, dependency audit).

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

- **Free, open-source (default setup):** Groq running `openai/gpt-oss-120b`. Get a free key at https://console.groq.com (no card needed).
- **Claude:** set `LLM_PROVIDER=anthropic` and `ANTHROPIC_API_KEY`. Paid, about 1–3 cents per message.
- **Any other OpenAI-compatible endpoint** (OpenRouter, Mistral, local Ollama…) works by changing `LLM_BASE_URL` and `LLM_MODEL`.

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

Open http://omniai.localhost:5173 (any `*.localhost` name reaches your machine; the hostname is `APP_DEV_HOST` in `frontend/src/brand.ts`, still named after the app's earlier name). The dev server proxies `/api` to the backend on port 8000. The launcher page (the dancing-MacBro wake screen used in production) is at http://omniai.localhost:5173/launcher.html.

**Tests**

```bash
cd backend
.venv\Scripts\python -m pytest -q      # backend, with a fake LLM: no API key needed
cd ../frontend
npm run build && npm run lint          # frontend type check, build and lint
```

## Code map

| Path | What it does |
|---|---|
| `backend/app/models.py` | Database schema (SQLAlchemy) |
| `backend/app/llm/tools.py` | Tool definitions + handlers the LLM can call |
| `backend/app/llm/prompt.py` | System prompt (stable, cached) + per-turn context |
| `backend/app/llm/chat.py` | One chat turn: fast paths → routing → tool loop → reply |
| `backend/app/llm/fastpath.py` | Messages answered by rules, without the AI |
| `backend/app/llm/provider.py`, `pool.py` | LLM providers and the model pool (Groq, other OpenAI-compatible APIs, Claude) |
| `backend/app/services/actions.py` | Confirm / reject / expire proposals: the only writer for AI proposals |
| `backend/app/services/foods.py` | Food library + recipes: units, scaling, recipe maths, typo matching |
| `backend/app/services/general_foods.py` | The built-in list of ~300 common foods |
| `backend/app/services/labels.py` | Pack labels for branded foods from Open Food Facts |
| `backend/app/nutrition.py` | BMR / TDEE / target calculation |
| `frontend/src/components/` | Home, ChatWidget + Chat (with voice input), ProposalCard, Dashboard (the Meals tab, with progress charts), Saved Food, Explore, Body Profile, Settings, GuideTour, Admin |

## Documentation

| Doc | For |
|---|---|
| [docs/user-guide.md](docs/user-guide.md) | User manual and walkthrough (the in-app **? Guide** tour is its short version) |
| [docs/hld.md](docs/hld.md) | High-level design with diagrams |
| [docs/technical-overview.md](docs/technical-overview.md) | Stack, API, data model, LLM layer, components, config, tests |
| [docs/llm-routing-strategy.md](docs/llm-routing-strategy.md) | Multi-model open-source routing plan |
| [docs/deployment.md](docs/deployment.md) | Deploying on Render with a Neon Postgres database |
| [docs/open-points.md](docs/open-points.md) | Ideas and decisions not built yet, and what's done |
| [macro_tracker_build_spec (1).md](macro_tracker_build_spec%20(1).md) | The original build spec |

Keep these in sync with every code or UI change. See the checklist in [docs/README.md](docs/README.md).

## Deployment

Production runs on free tiers: an always-on launcher page (Render static site `omniai-app`) shows a dancing-MacBro screen while the app (Render free web service, https://omniai-hkv2.onrender.com) wakes up, with data in Neon (free Postgres). Pushes to `main` deploy after CI passes. The web addresses still use the app's earlier name, OmniAI. See [docs/deployment.md](docs/deployment.md).

**Admin console:** reached through **Admin login** on the sign-in page, only for the configured admin email, with optional two-step sign-in. It shows users and activity with read-only access, and every view is written to an audit log.

## Design notes

- Proposed writes are stored in a `pending_actions` table instead of a `status=pending` column on `log_entries`, so proposed edits and deletes of confirmed entries also wait for confirmation.
- `log_entries.eaten_at` (when you ate) is separate from `created_at` (when you logged it). Deletes are soft (`deleted_at`).
- The schema is managed with Alembic (`backend/migrations`); migrations run on startup. To change it: edit the models, run `alembic revision --autogenerate -m "..."` in `backend/`, then review and commit the file.
- Not built yet: email verification codes, a scheduled cleanup of stale proposals, and more (see [docs/open-points.md](docs/open-points.md)).
