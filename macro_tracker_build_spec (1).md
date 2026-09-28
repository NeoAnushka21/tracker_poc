# Macro Tracker Chat App - Build Specification

## 1. Product Overview
A personal, conversational nutrition tracking web application. The user logs food by typing casual, natural-language messages describing what they ate (ingredients and quantities only, no macro numbers). An LLM parses the input, estimates calories, full macros (protein, carbohydrates, fats, fiber), and key micronutrients (e.g. vitamins, iron, magnesium), and the app tracks running totals against a personalized daily budget.

Primary goals of building this app (for context, not features):
- Personal daily use by a single user initially
- Serves as a learning project for LLM pipeline design (parsing, structured output, human-in-the-loop confirmation)
- Portfolio-worthy project

Out of scope for this version: workout tracking, social/multi-user features, mobile app, barcode scanning, photo-based food recognition. These may be added in later phases.

## 2. Target User (V1)
Single user (the app owner). Design the data model and logic to be generalizable to any user and any goal type (weight loss, muscle gain, weight gain, recomposition), even though only one user will use it initially. Do not hardcode assumptions toward a "cutting" goal.

## 3. Core User Flows

### 3.1 Onboarding
On first login, collect:
- Preferred name / nickname (optional) - what the user wants the LLM to call them (e.g. "buddy," "bro," a real name, or a nickname). Not compulsory; not necessarily their real/legal name.
- Age (store as date of birth) and sex - both required for the BMR formula
- Height
- Weight (stored as the first entry in weight_logs)
- Unit preference: metric or imperial (accept either as input, always store metric internally)
- Time zone: detect from the browser and confirm with the user; store as an IANA time zone name
- Goal type (weight loss / muscle gain / weight gain / recomposition - design as an extensible enum)
- Activity level / frequency

Using this, calculate maintenance calories using a standard scientific formula (e.g. Mifflin-St Jeor for BMR, multiplied by an activity factor for TDEE). Based on the stated goal, apply an appropriate calorie adjustment (deficit for weight loss, surplus for weight gain, smaller deficit or maintenance with higher protein for recomposition, surplus with protein target for muscle gain) and a macro split (protein/carbs/fat), with protein prioritized to preserve/build muscle. Present the resulting daily calorie budget and macro targets to the user, ideally editable.

### 3.2 Logging a Meal (Chat Interface)
1. User sends a free-text message describing what they ate, e.g. "had 100g cooked chicken, 10ml oil, 50g onion" or "had a guava" or "two glasses of water."
2. The LLM parses the message into structured ingredients + quantities.
3. If the LLM cannot confidently determine the ingredient composition (e.g. "had a sandwich" with no details) or the portion size (e.g. "had an ice cream" - cup vs scoop vs large serving), it must ask a clarifying follow-up question before proceeding. Do not silently guess when genuinely ambiguous. For unambiguous common items (e.g. "had a guava," "one glass of water"), proceed without asking.
4. Once ingredients and quantities are resolved, the LLM estimates calories, full macros (protein, carbs, fat, fiber), and key micronutrients (e.g. relevant vitamins, iron, magnesium) per ingredient and totals them for the entry.
   - If the user names a specific branded product (e.g. a particular whey protein brand and flavor), the LLM should not estimate from general knowledge alone - it should look up the actual product's nutrition label/facts (e.g. via web search) and use those real figures.
   - If the branded product cannot be found, the LLM should say so explicitly (e.g. "I couldn't find this product") and ask the user to provide the label's figures, rather than silently guessing or approximating a branded product's numbers.
5. The LLM presents this parsed result back to the user as a proposed log entry (human-readable summary) and asks for confirmation before saving.
6. If the user confirms ("looks good"), the entry is saved (posted) to the database.
7. If the user says something is wrong ("you got this wrong, correct this"), the LLM revises the entry based on the feedback and re-presents it for confirmation. Repeat until confirmed.
8. Meal type (breakfast/lunch/dinner/snack) is not manually tagged by the user. Infer it from timestamp of logging by default, but override based on explicit statements in the message (e.g. if logged at night but the user says "I had this for breakfast," tag it as breakfast).

Additional rules for logging:
- Water is logged like any other item: 0 kcal, quantity in ml (one glass is roughly 250 ml). No separate hydration goal or dedicated UI in V1.
- Meal-type inference uses the user's local time (from their stored time zone). Default windows: breakfast 05:00-11:00, lunch 11:00-15:00, snack 15:00-19:00, dinner 19:00-23:00; anything logged 23:00-05:00 is tagged as snack. Keep these as config constants.
- Timestamps are stored in UTC. Day boundaries and phrases like "today" or "last Tuesday" are resolved in the user's time zone.
- Pending entries (drafts awaiting confirmation) never count toward totals, dashboard figures, or query answers. Only confirmed entries do. Discard stale pending entries after a set period (e.g. 24 hours).

This confirm-before-write pattern (human-in-the-loop) applies to ALL write actions: creating, editing, and deleting log entries - not just initial logging.

### 3.3 Editing / Deleting via Chat
- User can request edits or deletions conversationally, e.g. "actually that chicken was 150g not 100g" or "delete the ice cream I logged earlier."
- The LLM must restate its understanding of the requested change and confirm with the user before applying it to the database.
- No silent writes: every create/update/delete is confirmed first.
- If a request could match more than one entry (e.g. two ice cream entries), the LLM must list the candidates (time, items, calories) and ask which one is meant. Never guess the target.

### 3.4 Querying Past Data via Chat
- User can ask natural-language questions about past logs, e.g. "what did I eat two days ago?" or "how many macros did I have last Tuesday?"
- The LLM answers these by calling backend tools (e.g. get_logs(start_date, end_date), get_daily_summary(date)) and summarizes the returned data conversationally. It never writes or runs SQL itself. Relative dates resolve in the user's time zone.

### 3.5 Dashboard
- Shows daily summary: calories/macros consumed vs. daily target/budget, ideally consumed and remaining.
- Toggle between Daily / Weekly / Monthly views of progress and trends (e.g. average intake, adherence to targets over time).
- No hourly granularity needed.
- Adherence (V1 default): a day counts as "on target" if calories are within +/-10% of the daily target and protein is at least 90% of its target. Weekly/monthly views show days on target out of days with logged entries. Keep thresholds as config constants.

## 4. LLM Behavior Requirements
- LLM must output structured data (JSON) for parsed ingredients: ingredient name, quantity, unit, estimated calories, protein (g), carbs (g), fat (g), fiber (g), and key micronutrients (e.g. relevant vitamins, iron, magnesium, as available).
- LLM must distinguish between confident estimates and genuinely ambiguous input requiring a follow-up question.
- For branded/named products, the LLM must attempt to find the actual product's real nutrition data (e.g. via web search) rather than estimating from general knowledge. Only if the specific product cannot be found should it inform the user and request the label figures directly, rather than silently approximating.
- LLM must never write to the database directly without an explicit user confirmation step in the conversation.
- Tool calling: the LLM touches data only through backend-defined tools (e.g. propose_entry, propose_edit, propose_delete, get_logs, get_daily_summary). Write operations execute only after an explicit user confirmation, and the backend enforces this in code (a pending -> confirmed transition triggered by the user's confirmation), not just through prompt instructions. The LLM never generates or runs raw SQL.
- No confidence score/indicator on estimates is required for this version - use best judgment on presentation; can be added later.

## 5. Suggested Technical Architecture

### 5.1 Stack
- Backend: Python, FastAPI (aligns with existing Python background)
- Frontend: React (Vite) single-page app with a chat interface and a dashboard (charts via a library such as Recharts), talking to the backend over a REST API. API-first design so a future mobile app can reuse the same backend.
- Database: Start with SQLite for simplicity (single user, no server setup); design schema so migration to PostgreSQL later is straightforward (use an ORM such as SQLAlchemy to keep this portable).
- LLM: Call a hosted LLM API directly using tool/function calling (default: Anthropic Claude API), rather than fine-tuning or self-hosting a model. Put the LLM behind a thin provider interface so the vendor or model can be swapped. Branded product lookups use the provider's web search tool. Later evolutions (RAG with a nutrition database, local models) are out of scope for V1.
- Auth: Email-based registration with OTP verification (single user for now, but build as a standard auth flow so it generalizes if ever extended to multiple users). User registers with an email address; an OTP is sent to that email to verify it before the account is considered valid/active. Combine with a password (hashed) or a passwordless OTP-based login flow. Use session or JWT-based auth for ongoing sessions after verification.
- Email delivery: a transactional email provider (e.g. Resend, SendGrid, or SMTP) is required to send OTP emails.
- OTP security: store only a hash of each OTP, expire codes after ~10 minutes, limit verification attempts, and rate-limit OTP sends per email.

### 5.2 High-Level Flow
1. User logs in via the website.
2. User sends a message in the chat interface.
3. Backend receives the message, sends it (with relevant context - recent conversation, user's profile/targets) to the LLM API with a system prompt defining its role, output format, and rules (ask clarifying questions when ambiguous, always confirm before writes, etc.).
4. LLM returns either (a) a clarifying question, or (b) a structured proposed log entry / edit / delete / query result.
5. Backend relays the LLM's response to the frontend chat UI.
6. If it's a proposed write action, user confirms or corrects via chat; loop back to step 3 until confirmed.
7. On confirmation, backend persists the entry to the database.
8. Dashboard queries the database directly (not via LLM) to render daily/weekly/monthly summaries and totals against targets.

### 5.3 Suggested Database Schema (starting point)
- users: id, email, email_verified (boolean), hashed_password, preferred_name (nullable), date_of_birth, sex, height_cm, unit_system (metric/imperial, display only), timezone (IANA name), goal_type, activity_level, created_at
- otp_verifications: id, user_id, email, otp_code_hash, expires_at, attempts, verified_at (nullable)
- weight_logs: id, user_id, weight_kg, logged_at (current weight = latest row; new rows are added when the user updates their weight, after which targets can be recalculated)
- user_targets: id, user_id, daily_calorie_target, protein_target_g, carbs_target_g, fat_target_g, effective_date (to allow target history if recalculated over time)
- log_entries: id, user_id, timestamp, meal_type (inferred), raw_user_message, status (confirmed/pending)
- log_entry_items: id, log_entry_id, ingredient_name, brand_name (nullable), quantity, unit, calories, protein_g, carbs_g, fat_g, fiber_g, micronutrients (JSON field storing available vitamins/minerals e.g. iron_mg, magnesium_mg, vitamin_c_mg, etc.)
- chat_messages: id, user_id, role (user/assistant), content, timestamp, related_log_entry_id (nullable) - for conversational history/context

### 5.4 Deployment (suggested, keep simple for V1)
- Local development first (run FastAPI + SQLite locally).
- When ready to deploy: a simple platform such as Render, Railway, or Fly.io for the backend, with the frontend either served from the same app or deployed separately (e.g. Vercel/Netlify if using React). No need for complex cloud infrastructure (Kubernetes, etc.) at this stage.

## 6. Explicit Scope Boundaries (V1)
Include:
- Chat-based food logging with LLM parsing and full nutrition estimation (calories, macros including fiber, and key micronutrients)
- Real product lookup for branded/named items, with fallback to asking the user for label figures if not found
- Human-in-the-loop confirmation for all writes (create/edit/delete)
- Clarifying follow-up questions for ambiguous ingredients or portions
- Onboarding with goal-based maintenance calorie and macro target calculation
- Dashboard with daily/weekly/monthly views
- Chat-based querying of past logs

Exclude (future phases):
- Workout tracking
- Mobile app
- Photo/barcode-based food recognition
- Multi-user/social features
- Confidence indicators on LLM estimates
- Fine-tuned or self-hosted LLMs, RAG-based nutrition lookups
