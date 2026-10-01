# Tandurust: working rules

## Documentation must stay in sync with the code

Any change to the code or UI must update the affected docs **in the same change**:

- `docs/user-guide.md`: the user manual (anything a user sees or does)
- `frontend/src/components/GuideTour.tsx`: the in-app first-run tour. Keep its steps consistent with the user guide.
- `docs/hld.md`: the high-level design and Mermaid diagrams (components, flows, tables, external services)
- `docs/technical-overview.md`: stack, API, data model, LLM layer, components, config, tests

Follow the checklist in `docs/README.md` and bump each touched file's "Last updated" date. A change isn't done until its docs are.

## Other rules

- Naming: the app is **Tandurust** (logo: the leaf-and-runner emblem in `frontend/public/brand/`, sources in `docs/brand/`; tagline "AI meal & wellness tracker"; renamed from OmniAI on 2026-09-30; Render services, addresses, log names and the dev host followed on 2026-10-01; only the Google Cloud project id and the forwarding site `omniai-app` keep "omniai"); **MacBro** is the chat assistant and appears, with its avatar, only in the chat (the chat window, its minimized bubble and the Home and Meals invites that open it), on the loading/wake screen (`WakeScreen`) and on the public welcome page (`frontend/welcome.html`: "Meet MacBro" and the example chats); all requested by the owner. Use `frontend/src/brand.ts` / `APP_NAME` in `config.py`; never hard-code the names.
- The LLM only proposes. Writes from chat go through `services/actions.py → confirm_action` after the user presses a button.
- Test with the fake LLM (`pytest`). Don't call real LLM APIs for routine testing, because the free-tier quota is shared.
- Stay open-source and free-tier. Don't add paid services or credits without asking.
- The admin email is fixed to `mhatre.anushka.work@gmail.com` for now. Admins are hidden from the user list.
- Production runs on **Postgres** (Neon); local dev and tests use SQLite. Before database-heavy changes, also run the tests with `TEST_DATABASE_URL` on a throwaway Postgres (see `docs/technical-overview.md` §10). Deployment steps: `docs/deployment.md`.
- **Open points:** anything discussed but not built (ideas, options offered, follow-ups, decisions against) goes into `docs/open-points.md` in the same change, with a date and status. Built items move to its **Done** section.
- Before committing: `backend: .venv\Scripts\python -m pytest -q` and `frontend: npm run build` must both pass.
