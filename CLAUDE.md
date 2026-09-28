# OmniAI: working rules

## Documentation must stay in sync with the code

Any change to the code or UI must update the affected docs **in the same change**:

- `docs/user-guide.md`: the user manual (anything a user sees or does)
- `frontend/src/components/GuideTour.tsx`: the in-app first-run tour. Keep its steps consistent with the user guide.
- `docs/hld.md`: the high-level design and Mermaid diagrams (components, flows, tables, external services)
- `docs/technical-overview.md`: stack, API, data model, LLM layer, components, config, tests

Follow the checklist in `docs/README.md` and bump each touched file's "Last updated" date. A change isn't done until its docs are.

## Other rules

- Naming: the app is **OmniAI** (placeholder logo "OAI"); **MacBro** is the chat assistant and appears, with its avatar, only in the Chat interface. Use `frontend/src/brand.ts` / `APP_NAME` in `config.py`; never hard-code the names.
- The LLM only proposes. Writes from chat go through `services/actions.py → confirm_action` after the user presses a button.
- Test with the fake LLM (`pytest`). Don't call real LLM APIs for routine testing, because the free-tier quota is shared.
- Stay open-source and free-tier. Don't add paid services or credits without asking.
- The admin email is fixed to `mhatre.anushka.work@gmail.com` for now. Admins are hidden from the user list.
- Production runs on **Postgres** (Neon); local dev and tests use SQLite. Before database-heavy changes, also run the tests with `TEST_DATABASE_URL` on a throwaway Postgres (see `docs/technical-overview.md` §10). Deployment steps: `docs/deployment.md`.
- Before committing: `backend: .venv\Scripts\python -m pytest -q` and `frontend: npm run build` must both pass.
