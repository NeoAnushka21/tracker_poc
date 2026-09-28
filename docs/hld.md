# MacBro high-level design (HLD)

> Last updated: 2026-09-28 (Home tab and streaks). Update the diagrams whenever a component, data flow, table or external service changes (see [docs/README.md](README.md)).
> Diagrams are Mermaid. They render on GitHub and in VS Code with a Mermaid preview extension.

## 1. Purpose and principles

MacBro is a chat-first calorie and macro tracker. Users describe food in natural language, an LLM estimates nutrition, and the user confirms before anything is stored.

**Design principles**

1. **The LLM proposes, the user disposes.** The model can only create *pending actions*. Every food, water or recipe write that comes from the chat goes through `confirm_action`, which only a user's button press can trigger.
2. **Deterministic numbers where possible.** Foods the user has already confirmed are stored in a personal library, and quantities are scaled in code, not by the model.
3. **Direct manipulation doesn't need the LLM.** Dashboard actions (move, copy, change quantity, delete, water buttons) write straight to the database, and the dashboard reads straight from it.
4. **Open-source, no paid credits at this stage.** The default model is open-weight (`gpt-oss-120b` on Groq's free tier). Claude is an optional provider behind the same interface. See [llm-routing-strategy.md](llm-routing-strategy.md).
5. **Degrade gracefully.** If the LLM is unavailable, users get a friendly "servers are temporarily down" message, and every non-chat feature keeps working.

## 2. System context

```mermaid
flowchart LR
    U([User<br/>browser]) -->|HTTPS| APP[MacBro web app]
    A([Admin<br/>browser]) -->|HTTPS · Admin login| APP
    APP -->|OpenAI-compatible API<br/>tool calling| LLM[(LLM provider<br/>Groq · gpt-oss-120b<br/>or Claude / Gemini / Ollama)]
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

    DB[(SQLite<br/>macro_tracker.db)]
    LLM[(LLM API)]

    SPA -->|/api/* JSON<br/>httpOnly JWT cookie| R
    S --> DB
    L -->|HTTPS| LLM
```

In development, Vite serves the SPA on `:5173` and proxies `/api` to Uvicorn on `:8000`.

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

- **Needs changes:** the user's correction is sent with `feedback_on_action_id`. The model proposes again, and the old card becomes *superseded*.
- **Cancel:** `POST /api/actions/{id}/reject`. Nothing is written except an event note that gives the model context.
- **Stop:** `POST /api/chat/cancel` marks the request cancelled. The backend checks it atomically before committing the reply (`finish_or_cancelled`). If it's too late, the UI keeps the reply.
- **Pending actions expire** after 24 hours, lazily on the next request.

### 4.2 Direct dashboard actions (no LLM)

```mermaid
flowchart LR
    D[Dashboard ⋯ menu] -->|POST /api/entries/items/id/transfer<br/>move or copy| E[services/entries]
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
| Provider | `LLM_PROVIDER=openai_compatible` (Groq by default) or `anthropic`, behind one `Provider` interface |
| Tools | Read: `get_food`, `get_logs`, `get_daily_summary`. Propose: `propose_entry`, `propose_edit`, `propose_delete`, `propose_move`, `propose_recipe`, `propose_water` |
| Prompt | Stable system prompt (MacBro persona and rules, cacheable) plus per-turn dynamic context (date, time, targets, today's totals, my foods, item ids) |
| History | Last `CHAT_HISTORY_MESSAGES` messages (12 on the free tier) |
| Guards | Energy balance, quantity cleanup, false "Logged" claim nudge, missed-water nudge, move-vs-delete guard |
| Failure | Any provider error → HTTP 503 with a friendly message (`SHOW_LLM_ERRORS=true` shows details in dev) |

## 7. Non-functional notes

| Area | Current state | Planned |
|---|---|---|
| **Security** | scrypt password hashes, JWT in an httpOnly SameSite cookie, per-user scoping on every query, admin audit | HTTPS + `COOKIE_SECURE`, rate limiting, OTP email verification |
| **Privacy** | Consent at sign-up (versioned), full account deletion | Data export |
| **Scale** | Single process, SQLite | Postgres (e.g. Neon), stateless app instances |
| **LLM capacity** | Groq free tier: about 200K tokens/day, 8K tokens/min | Multi-model routing across free providers, see [llm-routing-strategy.md](llm-routing-strategy.md) |
| **Accessibility** | WCAG AA contrast in light and dark, keyboard tooltips, ARIA tabs and dialogs | – |
| **Deployment** | Local only | Hosted frontend and backend (e.g. Render) with managed Postgres |
