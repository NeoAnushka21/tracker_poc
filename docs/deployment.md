# Deploying Tandurust (Render + Neon)

> Last updated: 2026-10-01 (moving to the Tandurust addresses: new services `tandurust` / `tandurust-app`, old `omniai-app` forwards, owner checklist; invite-only sign-up with a waitlist: `JOIN_MODE`, `LAUNCHER_ORIGIN`, how to open sign-up again; the static site's start page is now the welcome page, not the launcher; the app serves it at /welcome; 2026-09-30: UptimeRobot monitor live, server kept awake; keep-awake monitor steps, `/api/health` answers HEAD; monthly USDA food list check; earlier: always-on launcher page).

**Open the app from the welcome page:** https://tandurust-app.onrender.com (static site `tandurust-app`, never sleeps; the exact address is shown on its Render page). **App:** https://tandurust.onrender.com (Render service `tandurust`, Singapore). The old addresses: `omniai-app.onrender.com` forwards to the welcome page; `omniai-hkv2.onrender.com` (service `omniai`) is deleted once the move below is done · Neon project `young-star-73873699` (AWS Singapore). Local data was copied into Neon on 2026-09-29 (159 rows, 13 tables); Neon is now the real database. The NVIDIA backup is off in production. An UptimeRobot monitor (free, since 2026-09-30) pings `/api/health` every 5 minutes, so the app stays awake and down alerts go by email. Update this file whenever the deployment setup changes (see [README.md](README.md)).

> The app was renamed from OmniAI to **Tandurust** on 2026-09-30 (display) and its services and addresses followed on 2026-10-01: see [Moving to the Tandurust addresses](#moving-to-the-tandurust-addresses-2026-10-01). Until that checklist is done, the live app is still on the old `omniai` addresses.

Tandurust runs as **one free Render web service** that builds the React app and runs the FastAPI backend, which serves both the site and `/api`. The data lives in a **free Neon Postgres** database. Both are in **Singapore**, close to India and to each other. The setup is in [`render.yaml`](../render.yaml) at the repo root (a Render "Blueprint").

```mermaid
flowchart LR
    U[Browser] -->|HTTPS| R["Render web service (Singapore)<br/>FastAPI: site + /api"]
    R -->|SSL| N[("Neon Postgres (Singapore)")]
    R -->|HTTPS| G[(Groq: open-source models)]
    GH[GitHub: main branch] -->|push| CI[GitHub Actions CI]
    CI -->|all checks pass = deploy| R
```

**Who does what:** you create the accounts and paste secrets (steps marked **You**). Claude prepares the code, copies the data and checks the live site (steps marked **Claude**).

---

## Step 1: Push the code to GitHub (Claude, with your OK)

Render builds from the `main` branch of `github.com/NeoAnushka21/tracker_poc`. The repo contains no secrets: `backend/.env` and the `.db` file are git-ignored.

## Step 2: Create the Neon database (You, about 5 minutes)

1. Go to **https://neon.com** and click **Sign up**. Signing up with GitHub or Google is quickest. No card is needed.
2. On **Create project**, fill in:
   - **Project name:** `tandurust` (created as `omniai`; renaming it in Settings changes nothing else)
   - **Postgres version:** the default (17 or later)
   - **Cloud provider:** AWS
   - **Region:** **Asia Pacific (Singapore)**. This must match Render's region.
   - Leave **database name** as `neondb`.

   Click **Create project**.
3. On the project dashboard, click **Connect**. In the dialog:
   - **Branch:** `production` (the default), **Database:** `neondb`
   - Turn **Connection pooling off**. Our app keeps its own small connection pool, so it uses a direct connection.
   - Copy the connection string. It looks like `postgresql://neondb_owner:••••@ep-something.ap-southeast-1.aws.neon.tech/neondb?sslmode=require…`
4. **Treat this string as a password**: it contains the database password. Don't paste it into chat, email or code. You'll paste it in exactly two places: `backend/.env` (step 3) and Render (step 4).

## Step 3: Copy your existing data into Neon (You + Claude, about 2 minutes)

This copies every table (users, logs, chat, foods, water, weight, usage) from the local SQLite file into Neon. It keeps all ids, so logins, chat days and history work exactly as before. Passwords are copied as their hashes, so everyone keeps their current password.

1. **You:** open `backend/.env` and add one line at the end (the name matters; **not** `DATABASE_URL`, or your local app would start using the live database):

   ```
   TARGET_DATABASE_URL=postgresql://neondb_owner:...your Neon string...
   ```

2. **You:** stop using the local app (the copy should see the final state), then tell Claude it's there.
3. **Claude** runs, from `backend/`:

   ```
   .venv\Scripts\python scripts\copy_to_postgres.py
   ```

   It prints the row count per table and checks that the counts in Neon match. It **refuses** to run if Neon already has data, so it can't copy twice by accident. `--replace` wipes Neon first; use it only **before** the live app is in use (for example, if you logged more food locally before going live).

**After go-live, the Neon database is the real one.** The local SQLite file becomes a development copy: new logs made on the live site don't appear locally, and local ones don't appear online.

## Step 4: Create the Render service (You, about 5 minutes plus a build)

1. Sign in at **https://dashboard.render.com**.
2. Click **New +** → **Blueprint**.
3. **Connect the repository:**
   - If `tracker_poc` isn't listed, click **Configure account** / **Connect GitHub**.
   - Allow Render access to the `tracker_poc` repository only, then select it.
   - Branch: `main`.
4. Render reads `render.yaml` and shows the services: **tandurust** (free web service, Singapore: the app), **tandurust-app** (free static site: the welcome page, see below) and **omniai-app** (free static site forwarding the old address; neither static site needs secrets). It asks for the app's secret values:
   - **`DATABASE_URL`**: paste the same Neon connection string as in step 3.
   - **`LLM_API_KEY`**: your Groq key (the `LLM_API_KEY` value from `backend/.env`).
   - **`SECRET_KEY`**: a long random value (`python -c "import secrets; print(secrets.token_urlsafe(48))"`); when replacing a service, the old service's value instead.
   - `BREVO_API_KEY`, `EMAIL_FROM`, `SENTRY_DSN`: optional (sections below); leave empty if not set up.

   Everything else is preset. `GOOGLE_CLIENT_ID` (Continue with Google) is in `render.yaml`; it isn't a secret.
5. Click **Apply** / **Deploy Blueprint**. The first build takes about 3–6 minutes. You can watch it under the service's **Events** / **Logs**.
6. When it shows **Live**, the address is at the top of the service page, e.g. `https://tandurust.onrender.com`. If that name is taken, Render adds a suffix, such as `tandurust-ab12.onrender.com`. Then fix the lines marked `# address` in `render.yaml` (and `deploy/moved/index.html` if the welcome site got a suffix), and bookmark the welcome site's address.

Optional: the NVIDIA backup is **off** in production, because its free tier is for prototyping only. To turn it on, add `LLM_API_KEY_2` under the service's **Environment** tab.

## Step 5: Check the live site (Claude, then You)

- **Claude:** checks `/api/health`, the page load, and the logged-in screens (Home, Chat, Dashboard, Analysis, My Foods) on the live address.
- **You:** log in with your usual test-user email and password, and send one chat message such as "had 2 eggs".
- **Admin:** the admin account was copied too; log in with its current password.
- Everyone sees the **Before we continue** consent screen once, because the consent wording changed on 2026-09-28.

---

## Moving to the Tandurust addresses (2026-10-01)

Render can't change a service's `onrender.com` address, so `render.yaml` now describes **new** services: `tandurust` (the app) and `tandurust-app` (the welcome page). The old `omniai-app` site stays, but only forwards every visit to `tandurust-app` (`deploy/moved/index.html`, keeping any `#join` / `#login` part), so old bookmarks and invitation links keep working. The old app service `omniai` is deleted at the end. The data doesn't move: the new service uses the same Neon database. Free, about 30 minutes, all steps **You**:

1. **Copy the old secrets first.** Render → **omniai** → **Environment**: note `DATABASE_URL`, `LLM_API_KEY`, **`SECRET_KEY`**, `BREVO_API_KEY`, `EMAIL_FROM`, `SENTRY_DSN` (and `LLM_API_KEY_2` if set). `SECRET_KEY` matters most: the admin's two-step secret is encrypted with it, so a different key means setting two-step sign-in up again.
2. **Push this change**, then Render → **Blueprints** → the Blueprint → **Sync** / **Apply**. It offers to create `tandurust` and `tandurust-app` and to update `omniai-app`. Paste the values from step 1 when asked. (If it lists `omniai` as removed from the Blueprint, don't delete it yet.)
3. **Check the addresses.** When both new services are **Live**, read their addresses at the top of each service page. If either isn't exactly `tandurust.onrender.com` / `tandurust-app.onrender.com` (Render added a suffix), the `# address` lines in `render.yaml` and the address in `deploy/moved/index.html` need the real ones; push again.
4. **Google sign-in** (console.cloud.google.com → the project):
   - **Google Auth Platform → Clients → the web client:** add `https://tandurust.onrender.com` to **Authorised JavaScript origins** (keep the old one until step 9). Rename the client `Tandurust web` (optional; the client id doesn't change).
   - **Google Auth Platform → Branding:** app name `Tandurust`: what people see on Google's sign-in screen. If Google asks to verify the change, follow it (free).
   - **IAM & Admin → Settings:** project name `Tandurust` (display name only; the project id keeps "omniai" and can't be changed).
5. **UptimeRobot:** edit the monitor: friendly name `Tandurust app`, URL `https://tandurust.onrender.com/api/health`.
6. **Brevo** (if set up): if the sender name says OmniAI, change it to Tandurust (Senders); if `EMAIL_FROM` contains "OmniAI", update it in Render → **tandurust** → **Environment**.
7. **Sentry** (if set up): project settings → rename `omniai` to `tandurust` (optional; the DSN stays the same).
8. **Test** on https://tandurust-app.onrender.com: **Log in** (once more: logins are per address), Continue with Google, the admin's two-step code, one chat message; then open https://omniai-app.onrender.com and check it forwards. Update your bookmark and the phone home-screen shortcut.
9. **Clean up:** delete the old **omniai** web service (Render → **omniai** → **Settings** → **Delete web service**), so it doesn't build on every push or use free hours. Then remove `https://omniai-hkv2.onrender.com` from Google's authorised origins.
10. **Optional:** Neon → project **Settings** → rename to `tandurust`; rename your authenticator app's "OmniAI" entry (new set-ups already say Tandurust). The GitHub repository name can stay.

## The welcome page: no Render "waking up" page

The free web service sleeps after about 15 minutes idle, and Render shows its own black "waking up" page to browsers while it starts. That page can't be customised. So the Blueprint also creates **`tandurust-app`**, a free **static site** that never sleeps. Since 2026-10-01 its start page is the **welcome page** (`frontend/welcome.html`; before, a "launcher" wake screen):

1. You open the static site's address (bookmark and share this one, not the app's).
2. The welcome page shows at once and starts waking the app in the background (it polls `/api/health`, which allows other origins).
3. **Join** / **Log in** open the app's sign-up / login page (`#signup` / `#login`) as soon as it answers; until then the button shows a spinner and a note, and it moves on by itself (usually 30–60 s).
4. Old links with an app tab (e.g. `…/#dashboard`) are forwarded into the app the same way.
5. If the app falls asleep while it's open in a tab, the next action shows the dancing-MacBro wake screen as an overlay and continues by itself once the server is back.

The app serves the same welcome page at **`/welcome`** and sends everyone who isn't signed in there, so the app's own address starts at the welcome page too.

**After this change is pushed (You):** the static site's build command in `render.yaml` changed (`mv dist/welcome.html dist/index.html`). If Render doesn't pick it up by itself, open Render → **Blueprints** → the Blueprint → **Sync** / **Apply**, or set the build command on the `tandurust-app` service by hand.

**Adding it the first time (You):** after this change is pushed, Render → **Blueprints** → the Blueprint → it shows the new `tandurust-app` service → **Sync** / **Apply**. No secrets are needed. If the app's address ever changes, update `VITE_APP_URL` in `render.yaml`.

Since 2026-09-30 an uptime monitor keeps the server awake (see below), so the app's own address normally loads straight away too. Only after a restart or redeploy can Render's page still appear on the direct link; the launcher is still the safest link to share.

## Continue with Google (set up 2026-09-29)

Free: no billing and no Google review (only the basic `openid email profile` scopes). In the owner's Google Cloud project **Tandurust** (created as OmniAI):

1. **Google Auth Platform → Branding:** app name `Tandurust`, support and developer contact email. No logo (a logo needs Google's brand verification).
2. **Audience:** External, **published** (In production), so any Google account can sign in.
3. **Clients → Web application** `Tandurust web`. Authorised JavaScript origins: `https://tandurust.onrender.com`, `http://localhost:5173`, `http://localhost`. No redirect URIs; the client secret isn't used.
4. The client ID goes in `GOOGLE_CLIENT_ID` (`render.yaml` and `backend/.env`).

A new app address (e.g. a custom domain) must be added to the origins, or the button fails there.

## Monitoring: error reports and uptime (code ready 2026-09-29; accounts to create)

Every response has an `X-Request-ID`. An unexpected error shows the user "Something went wrong on our side (ref 1a2b3c4d)" and logs the full error with that id: search Render → **Logs** for the ref.

**Error reports (Sentry, free Developer plan)**, about 5 minutes:

1. Sign up at **https://sentry.io** (pick the EU or US data region when asked; either is fine).
2. **Create project** → platform **FastAPI** (or Python) → name `tandurust` → alert me on every new issue.
3. Copy the **DSN** (`https://…@….ingest.sentry.io/…`).
4. Render → **tandurust** → **Environment** → `SENTRY_DSN` → paste → **Save** (it redeploys).

Reports carry the error and stack trace only: no request bodies (chat, food, passwords), no local variables, no cookies or IP addresses, no performance tracing (`observability.setup_sentry`). GlitchTip (open source, Sentry-compatible) also works with the same `SENTRY_DSN`.

**Uptime alerts + keeping the server awake (UptimeRobot, free)**, about 5 minutes:

1. Sign up at **https://uptimerobot.com** (free plan: 50 monitors, checks every 5 minutes).
2. **+ New monitor**:
   - Monitor type: **HTTP(s)**
   - Friendly name: `Tandurust app`
   - URL: `https://tandurust.onrender.com/api/health` (the **app** address, not the static site: that one never sleeps)
   - Monitoring interval: **5 minutes**
   - Alert contact: your email
   - **Create monitor.**
3. Within a few minutes it shows **Up** (green). The free plan pings with `HEAD`; `/api/health` answers both `GET` and `HEAD` with 200 (since 2026-09-30; before that a `HEAD` got 405 and the monitor would have said "down").
4. Check after an hour: open the app's own address directly; it should load straight away, with no Render waking page.

Why it works: Render's free web service sleeps after ~15 minutes without a request; a request every 5 minutes means it never does. `/api/health` doesn't touch the database, so Neon still sleeps between real use (it wakes in about a second).

**Hours:** Render gives 750 free instance-hours a month per workspace, and one always-on service uses about 720-744. So keep **only one** free web service always on. A second free web service (e.g. the parked staging service) would share the same 750 hours and could use them up before the month ends, after which Render suspends free services until the next month; don't ping a staging service, and watch **Render → Billing → Free usage**. The launcher is a static site and uses no instance hours.

**Fallback:** cron-job.org (free) can call the same URL every 5-10 minutes if UptimeRobot changes its free plan. Render's docs don't say whether keep-alive pings are allowed; if that changes, pause the monitor or set its interval above 15 minutes to keep only the downtime alerts.

## Password-reset emails (Brevo, free; code ready 2026-09-29, account to create)

Without it, **Forgot password?** stays hidden on the live site. About 10 minutes:

1. Sign up at **https://www.brevo.com** (free plan, about 300 emails a day).
2. **Senders** (under Senders, domains & IPs): add the address emails should come from (e.g. your Gmail) and confirm it from the email Brevo sends.
3. **SMTP & API → API keys → Generate a new API key**. Copy it (it's shown once).
4. Render → **tandurust** → **Environment**: `BREVO_API_KEY` = the key, `EMAIL_FROM` = the verified sender → **Save**. `PUBLIC_APP_URL` is already set in `render.yaml`.
5. Test: on the live site, **Forgot password?** with your own email.

Emails sent from a free-mail address (Gmail) through another service can land in spam; with our own domain later, verify the domain in Brevo for better delivery. Menu names in Brevo may differ slightly. If sending fails, the reason is in Render → **Logs** (`tandurust.email`).

## Invite-only sign-up and the waitlist (2026-10-01)

`render.yaml` sets **`JOIN_MODE=waitlist`**: on the welcome page, **Join the waitlist** opens the waitlist form (with a clear "invite-only for now" note) instead of Create account, and new accounts (email or Google) are only allowed for emails approved in **Admin → Waitlist**. Existing accounts log in as usual. **`LAUNCHER_ORIGIN`** (`https://tandurust-app.onrender.com`) lets the always-on welcome site send the form to the app, and is the start of the link in invitation emails.

- **Emails:** each sign-up emails an alert to the admin address (`WAITLIST_ALERT_EMAIL`, default the fixed admin email), and **Approve** emails the person their invitation. Both use Brevo (section above). Until `BREVO_API_KEY` and `EMAIL_FROM` are set, nothing is sent (only logged): the list still fills up in **Admin → Waitlist**, and you tell approved people yourself (the panel says so).
- **Letting people in:** Admin → Waitlist → **Approve** (again: **Resend invite**). They create their account with the same email.
- **Open sign-up to everyone again:** Render → **tandurust** → **Environment** → `JOIN_MODE` = `open` → **Save** (the service restarts). Join goes back to Create account; the welcome page picks the change up on its next visit.
- **Test after a deploy:** open the static site in a private window → **Join** → the form appears → send it with a test address → the row shows in Admin → Waitlist (and the alert arrives, with Brevo set up) → **Remove** it.

## Security headers

The app sends a Content-Security-Policy and other security headers itself (see technical overview §4), and `/docs` is off in production. If something on the live page stops loading after adding an external script, font, frame or API, the browser console shows a CSP error: add that origin to `CONTENT_SECURITY_POLICY` in `backend/app/main.py`.

## How it behaves on the free plans

| What | Why | Effect |
|---|---|---|
| First visit after about 15 min idle takes **30–60 s** | Render's free service sleeps when idle | The welcome page shows at once and wakes it; Join / Log in wait with a spinner. Inside the app, the dancing-MacBro wake screen instead of Render's page. Later requests are fast. Rare since 2026-09-30: the UptimeRobot monitor keeps it awake; it can still happen right after a redeploy. |
| Database wakes in about a second after 5 min idle | Neon scales to zero | Barely noticeable. `/api/health` doesn't touch the database, so pingers don't keep Neon awake. |
| Limits | Render: 750 hours and 5 GB bandwidth a month. Neon: 0.5 GB storage, 100 compute hours a month. | Plenty for a beta |
| A push to `main` deploys **after CI passes** | `autoDeployTrigger: checksPass` (both services) | CI takes a few minutes, then the deploy about 3–6 min. A failed check means no deploy: the live app stays on the last good version. Tables and new columns are created on startup; data is kept. |

## CI: checks before every deploy (set up 2026-09-29)

`.github/workflows/ci.yml` runs on every push and pull request, free on GitHub Actions:

| Job | What it checks |
|---|---|
| Backend tests (SQLite) | `pytest -q` with the fake LLM (no keys, no quota) |
| Backend tests (Postgres, like production) | the same suite on a throwaway `postgres:17` service (`TEST_DATABASE_URL`) |
| Frontend type-check and build | `npm ci && npm run build` on Node 24 |
| Dependency vulnerability audit | `pip-audit` on `backend/requirements.txt`, `npm audit --omit=dev --audit-level=high` |

Render deploys `main` only when all four pass. See a run under the repository's **Actions** tab; a red X on a commit means it wasn't deployed. If an audit fails because of a newly published vulnerability, upgrade that package (or, if it can't be fixed yet and doesn't affect us, note why and relax the check) to unblock deploys. **One-time check:** Render → each service → **Settings** → **Auto-Deploy** should say **After CI Checks Pass** (the Blueprint sets it; if Blueprint sync is off, set it there by hand).

## Monthly USDA food list check (set up 2026-09-30)

`.github/workflows/usda-refresh.yml` runs at 03:00 UTC on the 1st of every month (or by hand: **Actions → USDA food list refresh → Run workflow**). It runs `backend/scripts/check_usda_updates.py`, which:

1. downloads the USDA SR Legacy data, rebuilds `backend/app/data/general_foods.json` and lists any food whose numbers changed (SR Legacy has been frozen since 2018, so normally none), and
2. lists USDA **Foundation Foods** added or removed since the last check (snapshot: `backend/app/data/usda_foundation_seen.json`; baseline 2026-09-30, 394 foods).

If nothing changed, it stops. Otherwise it opens (or updates) one pull request, **"USDA food list check YYYY-MM"**, on the branch `usda-refresh`, with the report as its text. Nothing reaches the app until you merge it. New foods aren't added automatically: to add one, give it a short name, aliases and raw/cooked in `backend/scripts/general_foods_spec.py` and rebuild (see the technical overview). Merging only records that they were seen.

**One-time setup:**
- GitHub → repository **Settings → Actions → General → Workflow permissions**: tick **Allow GitHub Actions to create and approve pull requests**. Without it, the run fails at the last step.
- Optional: a free USDA key from https://api.data.gov/signup as the Actions secret **`USDA_API_KEY`**. Without it the shared `DEMO_KEY` is used (about 10 requests an hour; a run needs 2–3).

Pull requests opened by this workflow don't start CI themselves (a GitHub rule for its built-in token). The checks run on `main` after you merge, and Render deploys only when they pass, as usual. Cost: free (GitHub Actions minutes and the USDA API).

## Updating and troubleshooting

- **Change a setting or key:** Render → service → **Environment** → edit → **Save**. It redeploys.
- **Build fails with a Node or Vite version error:** set `NODE_VERSION` to a newer version under **Environment**. The build log's first line prints the Node and Python versions.
- **"Set SECRET_KEY…" error at startup:** the app refuses to run on Postgres with the development key. Check that `SECRET_KEY` exists under **Environment**.
- **Chat says the servers are down:** check `LLM_API_KEY`, and the Groq quota under **Admin → AI usage**.
- **Admin lost the authenticator phone:** run `scripts/reset_admin_2fa.py <admin email>` from `backend/` with `DATABASE_URL` set to the Neon connection string (only for that command), then log in with the password and set two-step sign-in up again. Changing `SECRET_KEY` also makes the stored secret unreadable: set it up again.
- **Adding or upgrading a Python package:** edit `backend/requirements.in`, run `.venv\Scripts\python -m uv pip compile requirements.in --universal --python-version 3.14 -o requirements.txt` in `backend/`, test, and commit both files; Render installs the pinned `requirements.txt`. **Dependabot pull requests:** merge them once CI is green.
- **Database schema changes:** Alembic migrations run automatically at startup (`app/migrate.py`). To make one: edit `app/models.py`, then in `backend/` run `.venv\Scripts\alembic revision --autogenerate -m "what changed"`, review the new file in `migrations/versions/` (autogenerate misses renames and data changes), and commit it with the model change. `tests/test_migrations.py` fails if the models and migrations disagree. The first deploy with Alembic adopts the existing Neon database (marks it as the baseline, adds the missing `google_sub` index); nothing is deleted.
- **Before large database changes:** run the tests against a throwaway Postgres (`TEST_DATABASE_URL`, see technical-overview §10), because Postgres is stricter than SQLite. CI does this on every push too.
