# MacBro documentation

| Document | Audience | What it covers |
|---|---|---|
| [user-guide.md](user-guide.md) | End users, support, testers | Step-by-step manual: sign-up, logging, confirm cards, dashboard, analysis, foods, settings, FAQ |
| [hld.md](hld.md) | Everyone technical, stakeholders | High-level design: principles, context, containers, key flows, data model, non-functional notes (Mermaid diagrams) |
| [technical-overview.md](technical-overview.md) | Developers | Stack, repo layout, services, API, tables, LLM layer, frontend components, config, testing |
| [llm-routing-strategy.md](llm-routing-strategy.md) | Developers, product | Plan for routing across several free open-source models |

The in-app **first-run guide** (`frontend/src/components/GuideTour.tsx`) is the short version of `user-guide.md`.

## Keeping the docs current

The docs are part of the product. **Update them in the same change as the code**, not later. Use this checklist before every commit:

| If you changed… | Update |
|---|---|
| Anything a user sees or does (labels, buttons, tabs, flows, messages) | `user-guide.md` **and** the steps in `GuideTour.tsx` if the tour mentions it |
| A new screen, tab (e.g. Home), or major feature | `user-guide.md`, `GuideTour.tsx`, `hld.md` (container/flow), `technical-overview.md` (components) |
| An API endpoint | `technical-overview.md` §4 (and `hld.md` if it's a new flow) |
| A table or column | `technical-overview.md` §5 and the ER diagram in `hld.md` §5 |
| An LLM tool, guard, prompt rule or provider | `technical-overview.md` §6, `hld.md` §6 |
| Config / env variables | `technical-overview.md` §8, `backend/.env.example` |
| Target formulas, meal windows, water or micronutrient rules | `user-guide.md` (§2, §5, §11) and `technical-overview.md` |
| Deployment or infrastructure | `hld.md` §3 and §7, `technical-overview.md` §10, the root `README.md` |

Also bump the **Last updated** date at the top of each file you touch.
