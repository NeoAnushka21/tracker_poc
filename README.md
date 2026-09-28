# Macro Tracker

A chat-based calorie and macro tracker. You describe what you ate in plain language. Claude estimates the nutrition and proposes a log entry, and **nothing is saved until you click Confirm**.

Spec: [macro_tracker_build_spec (1).md](macro_tracker_build_spec%20(1).md). This is the **base version** (see "Scope" below).

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

**2. Frontend** (in a second terminal)

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173. The dev server proxies `/api` to the backend on port 8000.

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
- Meal type is inferred from your local time (breakfast 05–11, lunch 11–15, snack 15–19, dinner 19–23, otherwise snack). It's overridden when you say "for breakfast".
- Targets use Mifflin-St Jeor for BMR, multiplied by an activity factor for TDEE, then adjusted for your goal. Protein is set in g/kg, fat is 25% of calories, and carbs fill the rest. All the tunable numbers are in `backend/app/config.py`.

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
| `backend/app/nutrition.py` | BMR / TDEE / target calculation |
| `frontend/src/components/` | Auth, Onboarding, Chat, ProposalCard, Dashboard, Settings |

## Scope of this base version

**Included:** email + password login; onboarding (DOB, sex, height, weight, metric/imperial, time zone, goal, activity) with editable targets; chat logging with clarifying questions; proposal cards with confirm buttons; editing and deleting through chat; questions about past logs; a daily dashboard (calories, protein, carbs, fat, fiber) with previous-day navigation; weight updates with optional target recalculation.

**Deferred** (the schema already has room for these):

- OTP email verification
- Branded-product web search. For now Claude uses what it knows about the label and asks you for the figures if it doesn't know the product.
- Micronutrients (`log_entry_items.micronutrients` exists but is left empty)
- Weekly and monthly views and adherence (the thresholds are already in `config.py`)
- A cleanup job for stale proposals (they expire lazily on the next request)
- Deployment

**Differences from the spec's schema:**

- Proposed writes are stored in a `pending_actions` table instead of a `status=pending` column on `log_entries`. This gives proposed edits and deletes of confirmed entries somewhere to wait for confirmation too.
- `log_entries.eaten_at` (when you ate) is separate from `created_at` (when you logged it).
- Deletes are soft (`deleted_at`).
- Tables are created on startup. Add Alembic before changing the schema on a database with real data in it.
