# OmniAI technical overview

> Last updated: 2026-09-29 (wide-screen layouts). Update this file in the same change as any code change it describes (see [docs/README.md](README.md)).
> Architecture diagrams: [hld.md](hld.md). End-user manual: [user-guide.md](user-guide.md).

## 1. Tech stack

| Layer | Choice |
|---|---|
| Frontend | React 19, TypeScript, Vite. No UI or chart library: charts are hand-rolled SVG (`charts.tsx`). |
| Styling | One `styles.css` with CSS custom-property tokens (colours, `--radius` 16px / `--radius-sm` 12px, `--shadow-card`, `--accent-grad`, `--glass`). Light and dark via `prefers-color-scheme` and `data-theme`. **Responsive:** one layout for phones and tablets (a `max-width: 860px` block tightens spacing and grids), and from `min-width: 1024px` a "wide screens" block at the end of `styles.css` adds columns: Home (summary + streaks), Dashboard (`.dash-cols`: `.dash-summary` + `.dash-meals`), Analysis (`.analysis-charts`, 2 columns, CSS `order` pairs the cards), My foods (`.food-list`, 2 columns; `.food-row.editing` spans both). Content is capped by `--content-max` (1200px), and `--edge` gives the top bar, tabs and pages the same outer edge. Chat bubbles cap at 780px for line length. |
| Font | Plus Jakarta Sans (variable), self-hosted via `@fontsource-variable/plus-jakarta-sans` (no Google Fonts request) |
| Voice | Browser Web Speech API (`useSpeechToText.ts`), on-device or browser-vendor; no server audio. |
| Backend | Python 3.12+ (developed on 3.14), FastAPI, Uvicorn |
| ORM / DB | SQLAlchemy 2.x. Development: SQLite (`backend/macro_tracker.db`). Production: Postgres on Neon via `psycopg` 3 (`db.make_engine` rewrites `postgres://` URLs to the psycopg driver and pings pooled connections, since Neon suspends idle databases) |
| Hosting | One free Render web service (`render.yaml`, Singapore): builds the React app, and FastAPI serves it plus `/api`. See [deployment.md](deployment.md). |
| Auth | Email + password, stdlib `scrypt` hashes, PyJWT session token in an httpOnly cookie (`SESSION_DAYS`, default 14) |
| LLM | `openai` SDK against any OpenAI-compatible host (default Groq `openai/gpt-oss-120b`), or the `anthropic` SDK |
| Tests | pytest + FastAPI TestClient, with a `FakeProvider` in place of the LLM (no key or network needed) |

## 2. Repository layout

```
POC_new/
├── README.md                     # quick start
├── CLAUDE.md                     # rules for AI-assisted changes (keep docs in sync)
├── render.yaml                   # Render Blueprint (build, start, env vars)
├── .python-version               # Python version for Render (3.14)
├── docs/
│   ├── README.md                 # docs index + maintenance checklist
│   ├── user-guide.md             # end-user manual / walkthrough
│   ├── hld.md                    # high-level design (Mermaid diagrams)
│   ├── technical-overview.md     # this file
│   ├── deployment.md             # Render + Neon step-by-step
│   └── llm-routing-strategy.md   # multi-model open-source plan
├── backend/
│   ├── .env.example
│   ├── requirements.txt
│   ├── app/
│   │   ├── main.py               # FastAPI app, startup migrations, router wiring, serves frontend/dist
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
│   ├── scripts/copy_to_postgres.py  # one-off SQLite → Postgres data copy
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
| `chat` | `GET day?day=` (one local day of chat, default today, plus `prev_day`, the latest earlier day with messages) · `GET history` (legacy, last N) · `POST ""` (send; body may include `log_date`, a past day picked in the UI; 503 with friendly text if the LLM fails) · `POST cancel` |
| `actions` | `POST {id}/confirm` (returns the action + progress card) · `POST {id}/reject` |
| `dashboard` | `GET daily?date=` · `GET range?days=&end=` · `GET streaks` (logging and target streaks, best, last 7 days) |
| `entries` | `POST items/{id}/transfer` (move/copy) · `PATCH items/{id}` (quantity) · `DELETE items/{id}` |
| `foods` | `GET ""` · `GET {id}` · `PUT {id}` · `DELETE {id}` |
| `water` | `POST ""` · `DELETE {id}` |
| `admin` | `GET users` (admins excluded) · `GET users/{id}` · `GET users/{id}/chat` · `GET audit` · `GET llm-usage?hours=` (model calls, tokens, fast-path share, pool state; aggregate only, not audited). Every read of user data is audited. |

FastAPI's interactive docs are at `http://localhost:8000/docs` while the backend is running.

When `frontend/dist` exists (`FRONTEND_DIST`), `main.mount_frontend` also serves the built app: `/assets/*` as static files, and every other non-API path returns `index.html` (no-cache), so the site and the API share one address and one cookie. API routes are registered first and always win; unknown `/api/*` paths return 404.

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
| `llm_usage` | created_at, user_id, provider, model, tier, intent, prompt/completion tokens, latency_ms, outcome (ok / error / rate_limited / fastpath), escalated | One row per model call or rule-based reply. Kept (anonymised) after account deletion |

**Migrations.** Tables are created at startup, and `db.add_missing_columns()` adds new *nullable* columns to existing tables. `data_migrations.run_all()` handles one-off data fixes and creates the admin account from `ADMIN_INITIAL_PASSWORD` if it's missing. Adopt Alembic before non-additive schema changes or a move to Postgres.

## 6. LLM layer (`backend/app/llm/`)

| File | Role |
|---|---|
| `router.py` | Rule-based **routing**: intent (`query`, `edit`, `log`, `full`) and tier (`small` / `large`), plus the tools and prompt sections each intent gets. Leans towards `large` when unsure (vague dishes, 3+ foods, several meals, no amounts, recipes, feedback on a card, long messages). |
| `pool.py` | **Model pool**: models per tier from config (+ optional `llm_pool.json` providers). Primary models first (this tier, rotating, then the other tier), **backup** (priority 2) models only after every primary is unavailable. Per-provider timeouts. Rotates within a tier, fails over on errors, puts a model on **cooldown** on a 429 (using the host's "try again in 14m16s") or after 3 errors in a row, then falls back to the other tier before the friendly error. **Open source only:** a model is used only if its licence is in `ALLOWED_MODEL_LICENSES` (Apache-2.0, MIT). Licences are looked up per model version in `config.MODEL_LICENSES` (longest name prefix wins, e.g. GLM-5.3 is blocked but GLM-5.3-Flash is MIT; Mistral Large and Codestral are blocked); Llama, Gemma, Nemotron and Minitron are caught anywhere in the name; unknown models are blocked. |
| `fastpath.py` | **No-LLM replies** for common messages, creating the same cards through the same tool handlers: water amounts, "yes"/"ok" while a card is pending (points to the button), today's summary / "how much protein is left", foods that are all in My foods ("had 3 eggs for breakfast"), and "same breakfast as yesterday". Strict: anything unusual goes to the model. |
| `usage.py` | Collects one record per call during a turn; the chat router saves them after commit/rollback, so failed calls are counted. |
| `provider.py` | `AnthropicProvider` and `OpenAICompatibleProvider` behind `LLMProvider`. `to_openai_tools` uses `_relax` so optional fields aren't strictly required on OpenAI-compatible hosts. Retries once on a tool-validation error. Maps errors to a friendly message. `set_provider` injects the fake one in tests. |
| `prompt.py` | `SYSTEM_STABLE`: the MacBro persona and all logging rules (stable, so it can be cached). `build_dynamic_context`: local date and time, the picked day (`selected_date` with that day's entries and item ids) when set, meal window, targets, today's totals, recent entries with item ids, and the user's library foods. |
| `tools.py` | Tool schemas and handlers (below). Proposal handlers validate, scale library foods, run the energy check, then insert a `PendingAction`. |
| `chat.py` | `handle_user_message`: saves the user message (with `data.log_date` when a past day is picked), tries the **fast paths**, otherwise **routes** the message and runs the tool loop on that tier with only the routed tools and prompt sections, and `my_foods` limited to saved foods named in the message (or on a pending card). After `LLM_ESCALATE_AFTER_ERRORS` (2) validation errors on the small tier it **escalates** to the large tier with every tool. It builds history from **today's chat only** plus a `CHAT_DAY_GRACE_HOURS` (3 h) window before midnight (capped at `CHAT_HISTORY_MESSAGES`), runs the tool loop, applies the nudges, saves the reply, and checks for a cancel before committing. |

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
| `Chat` | Today's chat (fresh each day) with **Show earlier chat** loading previous days above a date divider; jumps to the latest message whenever the tab opens (`active` prop); **Logging for** date picker (sends `log_date`, tags the message); example chips, mic, Stop, feedback mode, progress card |
| `ProposalCard` | Renders each action type with Looks good / Needs changes / Cancel |
| `HomePage` | Default tab: time-of-day greeting, today's summary (reuses `CalorieRing`, `Bar`, `Water` from `Dashboard`), and the two streak cards |
| `Dashboard` | Day navigation, calorie ring, macro bars, calorie split, water, micronutrients, meal sections; each item has a pencil that opens an edit panel (Move/Copy toggle + meal dropdown, quantity, and icon buttons for edit in chat, delete, close). Shared icons live in `components/icons.tsx` |
| `AnalysisPage` + `charts.tsx` | 7/14/30-day range: stat tiles, line, bar and stacked charts with hover/keyboard tooltips and data tables |
| `FoodsPage` | Library search, filter, edit and delete |
| `SettingsDialog` | Account (and appearance), Targets (`TargetsEditor`), Body profile (`BodyProfile`), Password, Delete account |
| `AdminPage` | User table, per-user detail, audit log |
| `MacroChips` | Bold kcal plus colour-coded P / C / F / Fiber chips (chat cards, My foods) |
| `Avatar`, `ThemeToggle` | `AppLogo` (placeholder "OAI" tile, used everywhere outside the chat), `MacBroAvatar` (chat only), user avatar; theme switch (Settings only) |

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

## 8. Naming

**Local address:** http://omniai.localhost:5173. Browsers resolve any `*.localhost` name to this machine, so no hosts-file edit is needed. `omniai.com` is deliberately *not* mapped locally: it's a real public domain, and overriding it would hide the real site and confuse cookies. It becomes the address after deployment, if it can be registered. (`http://localhost:5173` still works, but it keeps a separate login cookie.)

The app is **OmniAI**; the chat assistant is **MacBro**. MacBro's name and avatar appear only inside the Chat tab (and in its replies). Everywhere else (header, login, consent, Home, guide tour, favicon, page title) uses the app name and the placeholder **OAI** logo until a real logo is designed. Names live in:

- `frontend/src/brand.ts`: `APP_NAME`, `APP_MARK` (logo text), `BOT_NAME`, `APP_DEV_HOST` (local address, `omniai.localhost`), `APP_DOMAIN` (planned public domain, `omniai.com`, not registered yet)
- `frontend/index.html` `<title>` is filled from `APP_NAME` by a small Vite plugin; `vite.config.ts` allows `APP_DEV_HOST`
- `frontend/public/favicon.svg` (the "OAI" mark)
- `backend/app/config.py`: `APP_NAME`, `BOT_NAME` (consent text uses `APP_NAME`)
- `backend/app/llm/prompt.py`: persona line ("MacBro … inside OmniAI")

## 9. Configuration

The environment is set in `backend/.env` (template: `backend/.env.example`):

| Variable | Purpose |
|---|---|
| `SECRET_KEY` | JWT signing key |
| `LLM_PROVIDER` | `openai_compatible` (default) or `anthropic` |
| `LLM_BASE_URL`, `LLM_MODEL`, `LLM_API_KEY` | OpenAI-compatible endpoint (Groq, Gemini, OpenRouter, Ollama…) |
| `ANTHROPIC_API_KEY` | When using Claude |
| `LLM_EFFORT`, `LLM_MAX_TOKENS`, `CHAT_HISTORY_MESSAGES` | Cost and quality tuning |
| `LLM_SMALL_MODELS`, `LLM_LARGE_MODELS` | Models per tier (default `openai/gpt-oss-20b` / `openai/gpt-oss-120b` on Groq) |
| `LLM_POOL_FILE` (`llm_pool.json`) + provider keys | Extra providers: per entry `tier`, `priority` (1 = rotates with the main models, 2 = backup only), `timeout_s`, `max_retries` (default 0). Currently NVIDIA `deepseek-v4.1-flash` as a large-tier backup, key `LLM_API_KEY_2`. Template: `backend/llm_pool.example.json` |
| `ALLOWED_MODEL_LICENSES` | Default `Apache-2.0,MIT` (open source only) |
| `LLM_ROUTING`, `LLM_FASTPATH` | Turn routing / rule-based replies off (both on by default) |
| `ADMIN_EMAILS`, `ADMIN_INITIAL_PASSWORD` | Admin accounts (default admin: `mhatre.anushka.work@gmail.com`) |
| `SHOW_LLM_ERRORS` | Development only |
| `DATABASE_URL` | Default: local SQLite. Production: the Neon connection string (`postgresql://…?sslmode=require`). On Postgres the app refuses to start with the development `SECRET_KEY`. |
| `COOKIE_SECURE`, `SESSION_DAYS` | `true` in production (HTTPS); session length |
| `FRONTEND_DIST` | Built frontend folder served by the backend (default `frontend/dist`) |
| `TARGET_DATABASE_URL`, `SOURCE_DATABASE_URL` | Only for `scripts/copy_to_postgres.py` (target Neon; source defaults to the local SQLite file) |
| `TEST_DATABASE_URL` | Only for tests: run the suite on a throwaway Postgres |

Production values live in the Render dashboard (`render.yaml` declares them; secrets are `sync: false` or generated), never in the repo.

Domain constants (meal windows, goal multipliers, activity factors, water, fiber, micronutrient reference values, adherence thresholds, consent text and version) are in `backend/app/config.py`.

## 10. Testing

```bash
cd backend
.venv\Scripts\python -m pytest -q      # 192 tests (1 needs Postgres), fake LLM, no network
cd ../frontend
npm run build                          # type-check + production build
```

- The Vite dev server uses a polling file watcher (`vite.config.ts`), and the backend should be started with `WATCHFILES_FORCE_POLLING=true`, because native file events were missed on Windows and served stale code.
- **Postgres:** production runs on Postgres, which is stricter than SQLite (e.g. `SELECT DISTINCT` can't compare JSON columns). Run the suite against a throwaway Postgres before database-heavy changes:

  ```bash
  docker run -d --rm --name omniai-pg-test -e POSTGRES_PASSWORD=test -e POSTGRES_DB=omniai -p 55432:5432 postgres:17
  set TEST_DATABASE_URL=postgresql://postgres:test@localhost:55432/omniai   # PowerShell: $env:TEST_DATABASE_URL="..."
  .venv\Scripts\python -m pytest -q
  ```

  Never point `TEST_DATABASE_URL` at real data: tables are dropped per test.
- `tests/conftest.py` gives each test a fresh database and a scripted `FakeProvider`. It also pins `ADMIN_EMAILS` and blanks `ADMIN_INITIAL_PASSWORD` so the local `.env` can't leak into tests.
- Coverage by file: `test_flow` (confirm loop, auth, guide flag), `test_foods` (library, recipes), `test_micros`, `test_water_meals`, `test_admin`, `test_analysis`, `test_entries` (move/copy/quantity/delete), `test_body`, `test_openai_provider`, `test_nutrition`, `test_streaks`, `test_chat_days`, `test_deploy` (URL handling, frontend serving, SQLite → Postgres copy), `test_routing` (router, fast paths, pool failover and cooldowns, licence gate, escalation, usage report).
- **Policy:** development and tests use the fake model. Don't use the real LLM API for routine testing, because the free-tier quota is shared with real users.

## 11. Known limitations and next steps

- A single process (one Render instance). The Stop-button registry and the model pool's cooldowns are in memory, so multiple instances would need Redis or the database; a restart (e.g. Render waking from sleep) forgets cooldowns.
- No Alembic yet; `add_missing_columns` only adds nullable columns.
- The free-tier LLM quota caps daily usage. Phases 1–3 of [llm-routing-strategy.md](llm-routing-strategy.md) are in (fast paths, routing, pool); a second provider (phase 4) and the evaluation run (phase 5) need decisions and accounts.
- Deferred: OTP email verification, branded-product web search, data export, a scheduled cleanup of stale proposals. Deployment is set up (Render + Neon, [deployment.md](deployment.md)); an uptime pinger and a custom domain are open decisions.
