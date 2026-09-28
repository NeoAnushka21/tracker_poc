# OmniAI high-level design (HLD)

> Last updated: 2026-09-29 (always-on launcher with wake screen). Update the diagrams whenever a component, data flow, table or external service changes (see [docs/README.md](README.md)).
> Diagrams are Mermaid. They render on GitHub and in VS Code with a Mermaid preview extension.

## 1. Purpose and principles

OmniAI is a chat-first calorie and macro tracker; its chat assistant is called MacBro. Users describe food in natural language, an LLM estimates nutrition, and the user confirms before anything is stored.

**Design principles**

1. **The LLM proposes, the user disposes.** The model can only create *pending actions*. Every food, water or recipe write that comes from the chat goes through `confirm_action`, which only a user's button press can trigger.
2. **Deterministic numbers where possible.** Foods the user has already confirmed are stored in a personal library, and quantities are scaled in code, not by the model.
3. **Direct manipulation doesn't need the LLM.** Dashboard actions (move, copy, change quantity, delete, water buttons) write straight to the database, and the dashboard reads straight from it.
4. **Open-source, no paid credits at this stage.** The default model is open-weight (`gpt-oss-120b` on Groq's free tier). Claude is an optional provider behind the same interface. See [llm-routing-strategy.md](llm-routing-strategy.md).
5. **Degrade gracefully.** If the LLM is unavailable, users get a friendly "servers are temporarily down" message, and every non-chat feature keeps working.

## 2. System context

```mermaid
flowchart LR
    U([User<br/>browser]) -->|HTTPS| APP[OmniAI web app]
    A([Admin<br/>browser]) -->|HTTPS · Admin login| APP
    APP -->|OpenAI-compatible API<br/>tool calling| LLM[(Open-source models<br/>Groq: gpt-oss-20b / 120b<br/>backup: NVIDIA DeepSeek V4.1 Flash)]
    U -.->|Web Speech API<br/>voice to text, in browser| U
```

| Actor | Uses |
|---|---|
| **User** | Home (summary and streaks), Chat logging, Dashboard, Analysis, My foods, Settings |
| **Admin** (emails in `ADMIN_EMAILS`) | Admin console only: user list, per-user read-only data, audit log |
| **LLM provider** | Nutrition estimation, clarifying questions, choosing tools. It never writes data. |

## 3. Container view

```mermaid
flowchart TB
    subgraph Browser
        SPA[React 19 + Vite SPA<br/>Home · Chat · Dashboard · Analysis · My foods<br/>Settings · Guide tour · Admin console]
        STT[Web Speech API]
        SPA --- STT
    end

    subgraph Server["FastAPI backend (Python)"]
        R[Routers<br/>auth · profile · chat · actions · dashboard<br/>entries · foods · water · admin]
        L[LLM layer<br/>prompt · tool loop · guards · provider]
        S[Services<br/>actions · logs · foods · entries · water<br/>analysis · progress · micros · accounts · cancel]
        N[nutrition.py<br/>Mifflin-St Jeor targets]
        R --> L
        R --> S
        L --> S
        S --> N
    end

    DB[(Postgres on Neon<br/>SQLite in development)]
    LLM[(LLM API)]

    SPA -->|/api/* JSON<br/>httpOnly JWT cookie| R
    S --> DB
    L -->|HTTPS| LLM
```

In development, Vite serves the SPA on `:5173` and proxies `/api` to Uvicorn on `:8000`, with SQLite as the database.

### 3.1 Production deployment

```mermaid
flowchart LR
    U[Browser] -->|1. open| L["Render static site omniai-app<br/>launcher: dancing MacBro<br/>never sleeps"]
    L -->|2. poll /api/health until awake| R
    U -->|3. app + /api over HTTPS| R["Render free web service · Singapore<br/>FastAPI serves the built SPA and /api<br/>sleeps after ~15 min idle"]
    R -->|SSL, pooled connections| N[("Neon Postgres · Singapore<br/>free, scales to zero")]
    R -->|HTTPS| G[(Groq: gpt-oss-20b / 120b)]
    GH[GitHub main] -->|push = build + deploy| R
```

The free web service sleeps when idle, and Render shows its own page while it wakes. So people open the always-on **launcher** (a free static site). It shows our wake screen until the app answers, then opens it. Inside the app, a request that hits the sleeping server shows the same wake screen as an overlay and is retried once the server is back. The app itself stays one service, keeping the site and the API on one address (simple same-site cookie, one cold start). The server and the database share a region because one chat message makes many database round trips. Secrets are set in the Render dashboard. Step-by-step: [deployment.md](deployment.md).

## 4. Key flows

### 4.1 Logging food through chat (the confirm loop)

```mermaid
sequenceDiagram
    actor User
    participant UI as React Chat
    participant API as POST /api/chat
    participant LLM as LLM (tool loop)
    participant T as Tools
    participant DB as Database

    User->>UI: "150g chicken and a cup of rice"
    UI->>API: message + client_request_id
    API->>DB: save user ChatMessage
    API->>LLM: system prompt + day context + history + tools
    LLM->>T: get_food / get_logs (read-only, optional)
    T-->>LLM: library match, confirmed data
    LLM->>T: propose_entry(items, meal, note)
    T->>T: guards: energy check (4/4/9 ±25%),<br/>library scaling, quantity cleanup
    T->>DB: INSERT pending_actions (status = pending)
    T-->>API: proposal + note (the turn ends)
    API-->>UI: reply + card "Not saved yet"
    User->>UI: Looks good
    UI->>API: POST /api/actions/{id}/confirm
    API->>DB: confirm_action: write log_entries + items,<br/>teach user_foods, mark action confirmed
    API-->>UI: action + "Day so far" progress card
```

- **One chat per day:** the UI shows today's chat (older days load on request), and the model only sees today's messages plus a 3-hour grace window, which keeps prompts small.
- **Date picker:** a past day picked in the chat is sent as `log_date`. The model gets that day's entries and logs or edits there by default.
- **Needs changes:** the user's correction is sent with `feedback_on_action_id`. The model proposes again, and the old card becomes *superseded*.
- **Cancel:** `POST /api/actions/{id}/reject`. Nothing is written except an event note that gives the model context.
- **Stop:** `POST /api/chat/cancel` marks the request cancelled. The backend checks it atomically before committing the reply (`finish_or_cancelled`). If it's too late, the UI keeps the reply.
- **Pending actions expire** after 24 hours, lazily on the next request.

### 4.1b Which model answers a message

```mermaid
flowchart TD
    M[User message] --> F{Fast path?<br/>water · yes · summary ·<br/>saved foods · same as yesterday}
    F -->|yes| C[Reply / card, no model call]
    F -->|no| R{Router rules}
    R -->|query · edit · simple log| S[Small tier<br/>gpt-oss-20b]
    R -->|vague dish · 3+ foods · recipe ·<br/>feedback · long| L[Large tier<br/>gpt-oss-120b]
    S -->|2 validation errors| L
    S & L --> P[(Model pool<br/>rotation · cooldown on 429 ·<br/>failover · open-source licence gate)]
    P -->|all unavailable| E[Friendly 'servers are down']
    P --> U[(llm_usage)]
```

### 4.2 Direct dashboard actions (no LLM)

```mermaid
flowchart LR
    D[Dashboard item edit panel] -->|POST /api/entries/items/id/transfer<br/>move or copy| E[services/entries]
    D -->|PATCH /api/entries/items/id<br/>quantity| E
    D -->|DELETE /api/entries/items/id| E
    W[Water buttons<br/>Home and Dashboard] -->|POST · DELETE /api/water| WS[services/water]
    H[Home streaks] -->|GET /api/dashboard/streaks| AN[services/analysis]
    AN --> DB
    E --> DB[(DB)]
    WS --> DB
    E -->|record_event| CM[chat event note<br/>so MacBro stays in sync]
```

### 4.3 Authentication and roles

```mermaid
flowchart TD
    Start([Open app]) --> Me{GET /api/auth/me}
    Me -->|401| Auth[Auth screen<br/>Log in · Create account · Admin login]
    Auth -->|user login / register + consent| Me
    Auth -->|admin-login, ADMIN_EMAILS only| Admin[Admin console]
    Me -->|is_admin| Admin
    Me -->|consent outdated| Consent[Consent gate]
    Consent --> Me
    Me -->|not onboarded| Onb[Onboarding → targets]
    Onb --> Me
    Me -->|guide not seen| Guide[First-run guide tour]
    Me --> Tabs[Home default · Chat · Dashboard · Analysis · My foods]
    Guide --> Tabs
```

Admin emails can't register or use the normal login. Admin accounts are hidden from the admin user list, and every admin view of a user's data is written to `admin_audit`.

## 5. Data model (overview)

```mermaid
erDiagram
    users ||--o{ weight_logs : has
    users ||--o{ user_targets : "has (dated)"
    users ||--o{ body_measurements : "has (optional)"
    users ||--o{ log_entries : logs
    log_entries ||--|{ log_entry_items : contains
    users ||--o{ water_logs : drinks
    users ||--o{ user_foods : "food library"
    user_foods ||--o{ recipe_ingredients : "recipe of"
    users ||--o{ pending_actions : "proposed writes"
    users ||--o{ chat_messages : "chat history"
    users ||--o{ admin_audit : "viewed by admin"
```

Column-level detail is in [technical-overview.md](technical-overview.md#5-data-model).

## 6. LLM layer at a glance

| Aspect | Design |
|---|---|
| Models | **Open-source only** (Apache 2.0 / MIT licences enforced in code). Two tiers on Groq's free tier: `gpt-oss-20b` (small) and `gpt-oss-120b` (large), in a quota-aware pool with cooldowns and failover; NVIDIA-hosted `deepseek-v4.1-flash` (MIT) as a slow backup used only when Groq is unavailable |
| Routing | L0 rule-based fast paths (no model) → rules pick intent + tier → small model, escalating to large on repeated validation errors |
| Tools | Read: `get_food`, `get_logs`, `get_daily_summary`. Propose: `propose_entry`, `propose_edit`, `propose_delete`, `propose_move`, `propose_recipe`, `propose_water` |
| Prompt | Stable system prompt (MacBro persona and rules, cacheable) plus per-turn dynamic context (date, time, targets, today's totals, my foods, item ids) |
| History | Today's chat only (+3 h grace): last 6 messages on the small tier, 12 on the large |
| Per-call size | Only the tools and prompt sections the intent needs, and only saved foods named in the message (25–87% fewer instruction tokens per call) |
| Observability | `llm_usage` table and the admin **AI usage** panel (calls, tokens, fast-path share, cooldowns) |
| Guards | Energy balance, quantity cleanup, false "Logged" claim nudge, missed-water nudge, move-vs-delete guard |
| Failure | Any provider error → HTTP 503 with a friendly message (`SHOW_LLM_ERRORS=true` shows details in dev) |

## 7. Non-functional notes

| Area | Current state | Planned |
|---|---|---|
| **Security** | scrypt password hashes, JWT in an httpOnly SameSite cookie (Secure over HTTPS in production), per-user scoping on every query, admin audit | Rate limiting, OTP email verification |
| **Privacy** | Consent at sign-up (versioned), full account deletion | Data export |
| **Scale** | Single process; Postgres on Neon (SQLite locally) | Stateless app instances (move in-memory state to the database or Redis) |
| **LLM capacity** | Groq free tier, per model (~200K tokens/day each for gpt-oss-20b and 120b); fast paths and slimmer calls stretch it | Second free provider for failover, see [llm-routing-strategy.md](llm-routing-strategy.md) |
| **Accessibility** | WCAG AA contrast in light and dark, keyboard tooltips, ARIA tabs and dialogs | – |
| **Responsive layout** | Phone/tablet: one column. Laptop (≥1024px): multi-column pages capped at 1200px, same top tabs. CSS only, no separate mobile app. | – |
| **Deployment** | Live at `omniai-hkv2.onrender.com`: Render free web service + Neon free Postgres, Singapore; the free service sleeps after ~15 min idle (30–60 s first load) | Uptime pinger, custom domain, Alembic migrations |
