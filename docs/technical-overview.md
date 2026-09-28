# MacBro technical overview

> Last updated: 2026-09-28 (Home tab and streaks). Update this file in the same change as any code change it describes (see [docs/README.md](README.md)).
> Architecture diagrams: [hld.md](hld.md). End-user manual: [user-guide.md](user-guide.md).

## 1. Tech stack

| Layer | Choice |
|---|---|
| Frontend | React 19, TypeScript, Vite. No UI or chart library: charts are hand-rolled SVG (`charts.tsx`). |
| Styling | One `styles.css` with CSS custom-property tokens (colours, `--radius` 16px / `--radius-sm` 12px, `--shadow-card`, `--accent-grad`, `--glass`). Light and dark via `prefers-color-scheme` and `data-theme`. |
| Font | Plus Jakarta Sans (variable), self-hosted via `@fontsource-variable/plus-jakarta-sans` (no Google Fonts request) |
| Voice | Browser Web Speech API (`useSpeechToText.ts`), on-device or browser-vendor; no server audio. |
| Backend | Python 3.12+ (developed on 3.14), FastAPI, Uvicorn |
| ORM / DB | SQLAlchemy 2.x, SQLite (`backend/macro_tracker.db`) |
| Auth | Email + password, stdlib `scrypt` hashes, PyJWT session token in an httpOnly cookie (`SESSION_DAYS`, default 14) |
| LLM | `openai` SDK against any OpenAI-compatible host (default Groq `openai/gpt-oss-120b`), or the `anthropic` SDK |
| Tests | pytest + FastAPI TestClient, with a `FakeProvider` in place of the LLM (no key or network needed) |

## 2. Repository layout

```
POC_new/
├── README.md                     # quick start
├── CLAUDE.md                     # rules for AI-assisted changes (keep docs in sync)
├── docs/
│   ├── README.md                 # docs index + maintenance checklist
│   ├── user-guide.md             # end-user manual / walkthrough
│   ├── hld.md                    # high-level design (Mermaid diagrams)
│   ├── technical-overview.md     # this file
│   └── llm-routing-strategy.md   # multi-model open-source plan
├── backend/
│   ├── .env.example
│   ├── requirements.txt
│   ├── app/
│   │   ├── main.py               # FastAPI app, startup migrations, router wiring
│   │   ├── config.py             # every tunable constant + env settings
│   │   ├── db.py                 # engine, session, add_missing_columns()
│   │   ├── data_migrations.py    # one-off data fixes + admin bootstrap
│   │   ├── models.py             # SQLAlchemy models
│   │   ├── schemas.py            # Pydantic request bodies
│   │   ├── security.py           # password hashing, JWT
│   │   ├── deps.py               # current_user / admin_user / onboarded_user
│   │   ├── nutrition.py          # BMR / TDEE / targets
│   │   ├── timeutil.py           # time zones, local day bounds
│   │   ├── routers/              # HTTP endpoints (section 4)
│   │   ├── services/             # business logic (section 3)
│   │   └── llm/                  # prompt, tools, tool loop, providers (section 6)
│   └── tests/                    # pytest suite
└── frontend/
    ├── vite.config.ts            # dev proxy /api → :8000
    └── src/
        ├── App.tsx               # auth gate, tabs (Home default), top bar, guide tour
        ├── api.ts                # typed fetch client
        ├── types.ts, format.ts, theme.ts, useSpeechToText.ts
        ├── styles.css
        └── components/           # section 7
```

## 3. Backend services

| Module | Responsibility |
|---|---|
| `services/actions.py` | Pending-action lifecycle: `confirm_action` (the only writer for LLM proposals: create, edit, delete, move, copy, water, save_recipe), `reject_action`, `supersede_older`, `expire_stale` (24 h) |
| `services/logs.py` | Totals, `daily_summary` (macros, micros, water, targets), `logs_by_day`, current targets and weight |
| `services/foods.py` | Food library: unit normalisation, `scale_factor`, `resolve_library_item`, `upsert_estimate` (teach on confirm, never overwrite user-edited foods), `compute_recipe`, `save_recipe` |
| `services/entries.py` | Direct item operations: `transfer_items` (move/copy), `set_item_quantity`, `delete_item` (soft-deletes an empty entry), `record_event` (chat note so the model knows) |
| `services/water.py` | Water target (35 ml/kg + activity extra), add/delete, daily summary |
| `services/analysis.py` | `range_summary` for 7/14/30 days, `on_target` (±10% kcal, ≥90% protein); `streaks` (365-day window; today only counts once it qualifies, so it never breaks a streak) |
| `services/progress.py` | "Day so far" card after a confirm: percentages and a template motivational line |
| `services/micros.py` | Clean, scale and total the micronutrient JSON |
| `services/cancel.py` | In-memory registry for the Stop button: `start`, `raise_if_cancelled`, `finish_or_cancelled` (atomic check before commit), `cancel` |
| `services/accounts.py` | `delete_user_and_data`: removes every row the user owns, keeps and unlinks the admin audit trail |

## 4. HTTP API

All endpoints are JSON under `/api`, authenticated by the session cookie. Every query is scoped to the current user.

| Router | Endpoints |
|---|---|
| `auth` | `GET consent-text` · `POST register` (needs `consent`; blocks admin emails) · `POST login` (blocks admin emails) · `POST admin-login` (only `ADMIN_EMAILS`) · `POST change-password` · `POST delete-account` · `POST logout` · `POST consent` · `POST guide-seen` · `GET me` |
| `profile` | `POST onboarding` · `GET preview-targets` · `PUT targets` · `POST weight` · `GET body` · `POST height` · `POST measurements` · `DELETE measurements/{id}` |
| `chat` | `GET history` · `POST ""` (send; 503 with friendly text if the LLM fails) · `POST cancel` |
| `actions` | `POST {id}/confirm` (returns the action + progress card) · `POST {id}/reject` |
| `dashboard` | `GET daily?date=` · `GET range?days=&end=` · `GET streaks` (logging and target streaks, best, last 7 days) |
| `entries` | `POST items/{id}/transfer` (move/copy) · `PATCH items/{id}` (quantity) · `DELETE items/{id}` |
| `foods` | `GET ""` · `GET {id}` · `PUT {id}` · `DELETE {id}` |
| `water` | `POST ""` · `DELETE {id}` |
| `admin` | `GET users` (admins excluded) · `GET users/{id}` · `GET users/{id}/chat` · `GET audit`. Every read of user data is audited. |

FastAPI's interactive docs are at `http://localhost:8000/docs` while the backend is running.

## 5. Data model

| Table | Key columns | Notes |
|---|---|---|
| `users` | email, hashed_password, preferred_name, date_of_birth, sex, height_cm, unit_system, timezone, goal_type, activity_level, consent_at, consent_version, last_login_at, login_count, guide_seen_at | `onboarded` = DOB and goal set. `guide_seen_at` stops the first-run tour reopening. |
| `weight_logs` | weight_kg, logged_at | Latest row = current weight |
| `user_targets` | daily_calorie_target, protein/carbs/fat_target_g, effective_date, is_custom | Dated: history is kept, and the latest effective row applies |
| `body_measurements` | measured_at, neck/chest/waist/hips/biceps/forearm/thigh/calf `_cm` | Optional, any subset per row |
| `log_entries` | eaten_at (UTC), meal_type, raw_user_message, deleted_at | Soft delete. `meal_type` ∈ breakfast, morning_snack, lunch, evening_snack, dinner |
| `log_entry_items` | ingredient_name, brand_name, quantity, unit, calories, protein_g, carbs_g, fat_g, fiber_g, micronutrients (JSON) | Nutrients are stored, not recomputed, so past logs never change |
| `water_logs` | amount_ml, drank_at | |
| `user_foods` | name, name_key, brand_name, kind (food/recipe), source, ref_qty, ref_unit, macros, grams_per_piece/serving, micronutrients, yield_pieces/servings, cooked_weight_g, last_used_at | Personal library. Values are per reference amount. |
| `recipe_ingredients` | recipe_id → user_foods, food_id → user_foods, quantity, unit | |
| `pending_actions` | action_type, target_entry_id, payload (JSON), status, chat_message_id, result_entry_id, resolved_at | Status: pending → confirmed / rejected / superseded / expired |
| `chat_messages` | role (user/assistant/event), content, kind (e.g. `progress`), data (JSON), related_log_entry_id | `event` rows are context for the model and hidden in the UI |
| `admin_audit` | admin_user_id, target_user_id, action | Kept after account deletion (unlinked) |

**Migrations.** Tables are created at startup, and `db.add_missing_columns()` adds new *nullable* columns to existing tables. `data_migrations.run_all()` handles one-off data fixes and creates the admin account from `ADMIN_INITIAL_PASSWORD` if it's missing. Adopt Alembic before non-additive schema changes or a move to Postgres.

## 6. LLM layer (`backend/app/llm/`)

| File | Role |
|---|---|
| `provider.py` | `AnthropicProvider` and `OpenAICompatibleProvider` behind `LLMProvider`. `to_openai_tools` uses `_relax` so optional fields aren't strictly required on OpenAI-compatible hosts. Retries once on a tool-validation error. Maps errors to a friendly message. `set_provider` injects the fake one in tests. |
| `prompt.py` | `SYSTEM_STABLE`: the MacBro persona and all logging rules (stable, so it can be cached). `build_dynamic_context`: local date and time, meal window, targets, today's totals, recent entries with item ids, and the user's library foods. |
| `tools.py` | Tool schemas and handlers (below). Proposal handlers validate, scale library foods, run the energy check, then insert a `PendingAction`. |
| `chat.py` | `handle_user_message`: saves the user message, builds history (`CHAT_HISTORY_MESSAGES`), runs the tool loop, applies the nudges, saves the reply, and checks for a cancel before committing. |

**Tools**

| Tool | Kind | Effect |
|---|---|---|
| `get_food` | read | Look up the user's library by name |
| `get_logs` | read | Confirmed entries for a date range |
| `get_daily_summary` | read | Totals against targets for a day |
| `propose_entry` | propose | New meal → `create` action |
| `propose_edit` | propose | Replace an entry's items → `edit` |
| `propose_delete` | propose | → `delete` |
| `propose_move` | propose | Move or copy items to another meal/date → `move` / `copy` |
| `propose_recipe` | propose | → `save_recipe` |
| `propose_water` | propose | → `water` |

**Guards in code (not just the prompt)**

- **Energy balance:** each item's kcal must be within ±25% of 4·P + 4·C + 9·F. Alcohol is exempt. Otherwise the tool returns an error and the model must recalculate.
- **Quantity cleanup:** strips a leading quantity duplicated in the name ("50 g rice" at 50 g becomes "rice").
- **False-claim nudge:** a reply that says "logged/saved" without a proposal is sent back once. Any remaining "Logged…" wording becomes "Here's…".
- **Missed-water nudge:** if the message mentions water but no `propose_water` was made.
- **Move vs delete:** a move request must use `propose_move`, never delete + create.
- **One call per meal:** proposals carry the reply in `note`, which ends the turn.

**Failure handling:** a provider exception returns HTTP 503 with `LLM_UNAVAILABLE_MESSAGE` ("MacBro's servers are temporarily down…"). `SHOW_LLM_ERRORS=true` shows the raw error in development.

## 7. Frontend

| Component | Purpose |
|---|---|
| `App.tsx` | Loads `/me`, then routes: auth screen → admin console, or consent gate → onboarding → tabbed app (Home, Chat, Dashboard, Analysis, My foods; Home is the default). Tabs live in the URL hash. Owns `dataVersion` (bumped after writes so views refetch) and the first-run guide. |
| `AuthScreen` | Log in / Create account (with consent) / Admin login modes |
| `ConsentGate` | Re-consent when `CONSENT_VERSION` changes |
| `Onboarding` | Profile form, then editable target preview |
| `GuideTour` | First-run walkthrough docked at the bottom. It switches tabs per step and calls `POST /auth/guide-seen` when closed. The **? Guide** button reopens it. **Its steps must match `docs/user-guide.md`.** |
| `Chat` | Messages, example chips, mic, Stop, feedback mode, progress card |
| `ProposalCard` | Renders each action type with Looks good / Needs changes / Cancel |
| `HomePage` | Default tab: time-of-day greeting, today's summary (reuses `CalorieRing`, `Bar`, `Water` from `Dashboard`), and the two streak cards |
| `Dashboard` | Day navigation, calorie ring, macro bars, calorie split, water, micronutrients, meal sections with the ⋯ item menu |
| `AnalysisPage` + `charts.tsx` | 7/14/30-day range: stat tiles, line, bar and stacked charts with hover/keyboard tooltips and data tables |
| `FoodsPage` | Library search, filter, edit and delete |
| `SettingsDialog` | Account (and appearance), Targets (`TargetsEditor`), Body profile (`BodyProfile`), Password, Delete account |
| `AdminPage` | User table, per-user detail, audit log |
| `MacroChips` | Bold kcal plus colour-coded P / C / F / Fiber chips (chat cards, My foods) |
| `Avatar`, `ThemeToggle` | MacBro and user avatars; theme switch (Settings only) |

**Colour tokens** (checked with the dataviz palette validator for colour-vision deficiency separation and contrast):

| Token | Light | Dark |
|---|---|---|
| Protein | `#1db371` | `#1fa855` |
| Fiber | `#c73e91` | `#c73e91` |
| Carbs | `#e07b12` | `#e0730f` |
| Fat | `#0b8fc9` | `#0b8fc9` |
| Water | `#4a3aa7` | `#9085e9` |

Light passes every check (worst colour-blind separation ΔE 9.4). Dark is in the 6–8 "floor" band (ΔE 7.9, green vs amber), which is allowed because every bar, chip and legend also carries a text label. Text always uses text tokens, never a series colour; neutral text tokens pass WCAG AA on every surface.

**Visual language:** slate off-white background (`#f8fafc`) with white cards and soft shadows; pill tabs with a sliding gradient underline (`App.tsx` measures the active tab); a pill-shaped chat input with gradient Send and mic buttons; a mint-tinted proposal card with row dividers only; a large glowing calorie ring; 14px macro bars; charts with rounded bar tops, dashed grid lines, no axis lines, and an arrow tooltip; Analysis stat cards with faint background icons; My foods as cards with hover-revealed icon buttons.

## 8. Configuration

The environment is set in `backend/.env` (template: `backend/.env.example`):

| Variable | Purpose |
|---|---|
| `SECRET_KEY` | JWT signing key |
| `LLM_PROVIDER` | `openai_compatible` (default) or `anthropic` |
| `LLM_BASE_URL`, `LLM_MODEL`, `LLM_API_KEY` | OpenAI-compatible endpoint (Groq, Gemini, OpenRouter, Ollama…) |
| `ANTHROPIC_API_KEY` | When using Claude |
| `LLM_EFFORT`, `LLM_MAX_TOKENS`, `CHAT_HISTORY_MESSAGES` | Cost and quality tuning |
| `ADMIN_EMAILS`, `ADMIN_INITIAL_PASSWORD` | Admin accounts (default admin: `mhatre.anushka.work@gmail.com`) |
| `SHOW_LLM_ERRORS` | Development only |
| `DATABASE_URL`, `COOKIE_SECURE`, `SESSION_DAYS` | Deployment |

Domain constants (meal windows, goal multipliers, activity factors, water, fiber, micronutrient reference values, adherence thresholds, consent text and version) are in `backend/app/config.py`.

## 9. Testing

```bash
cd backend
.venv\Scripts\python -m pytest -q      # 131 tests, fake LLM, no network
cd ../frontend
npm run build                          # type-check + production build
```

- The Vite dev server uses a polling file watcher (`vite.config.ts`), because native file events were missed on Windows and served stale modules.
- `tests/conftest.py` gives each test a fresh database and a scripted `FakeProvider`. It also pins `ADMIN_EMAILS` and blanks `ADMIN_INITIAL_PASSWORD` so the local `.env` can't leak into tests.
- Coverage by file: `test_flow` (confirm loop, auth, guide flag), `test_foods` (library, recipes), `test_micros`, `test_water_meals`, `test_admin`, `test_analysis`, `test_entries` (move/copy/quantity/delete), `test_body`, `test_openai_provider`, `test_nutrition`, `test_streaks`.
- **Policy:** development and tests use the fake model. Don't use the real LLM API for routine testing, because the free-tier quota is shared with real users.

## 10. Known limitations and next steps

- SQLite and a single process. The Stop-button registry is in memory, so multiple instances would need Redis or the database.
- No Alembic yet; `add_missing_columns` only adds nullable columns.
- The free-tier LLM quota caps daily usage. Plan: [llm-routing-strategy.md](llm-routing-strategy.md).
- Deferred: OTP email verification, branded-product web search, data export, a scheduled cleanup of stale proposals, and deployment (planned: hosted backend, e.g. Render, with Postgres, e.g. Neon).
