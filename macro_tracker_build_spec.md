# Macro Tracker Chat App - Build Specification

## 1. Product Overview
A personal, conversational macro and calorie tracking web application. The user logs food by typing casual, natural-language messages describing what they ate (ingredients and quantities only, no macro numbers). An LLM parses the input, estimates calories and macros, and the app tracks running totals against a personalized daily calorie/macro budget.

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
- Height
- Weight
- Goal type (weight loss / muscle gain / weight gain / recomposition - design as an extensible enum)
- Activity level / frequency

Using this, calculate maintenance calories using a standard scientific formula (e.g. Mifflin-St Jeor for BMR, multiplied by an activity factor for TDEE). Based on the stated goal, apply an appropriate calorie adjustment (deficit for weight loss, surplus for weight gain, smaller deficit or maintenance with higher protein for recomposition, surplus with protein target for muscle gain) and a macro split (protein/carbs/fat), with protein prioritized to preserve/build muscle. Present the resulting daily calorie budget and macro targets to the user, ideally editable.

### 3.2 Logging a Meal (Chat Interface)
1. User sends a free-text message describing what they ate, e.g. "had 100g cooked chicken, 10ml oil, 50g onion" or "had a guava" or "two glasses of water."
2. The LLM parses the message into structured ingredients + quantities.
3. If the LLM cannot confidently determine the ingredient composition (e.g. "had a sandwich" with no details) or the portion size (e.g. "had an ice cream" - cup vs scoop vs large serving), it must ask a clarifying follow-up question before proceeding. Do not silently guess when genuinely ambiguous. For unambiguous common items (e.g. "had a guava," "one glass of water"), proceed without asking.
4. Once ingredients and quantities are resolved, the LLM estimates calories and macros (protein, carbs, fat) per ingredient and totals them for the entry.
5. The LLM presents this parsed result back to the user as a proposed log entry (human-readable summary) and asks for confirmation before saving.
6. If the user confirms ("looks good"), the entry is saved (posted) to the database.
7. If the user says something is wrong ("you got this wrong, correct this"), the LLM revises the entry based on the feedback and re-presents it for confirmation. Repeat until confirmed.
8. Meal type (breakfast/lunch/dinner/snack) is not manually tagged by the user. Infer it from timestamp of logging by default, but override based on explicit statements in the message (e.g. if logged at night but the user says "I had this for breakfast," tag it as breakfast).

This confirm-before-write pattern (human-in-the-loop) applies to ALL write actions: creating, editing, and deleting log entries - not just initial logging.

### 3.3 Editing / Deleting via Chat
- User can request edits or deletions conversationally, e.g. "actually that chicken was 150g not 100g" or "delete the ice cream I logged earlier."
- The LLM must restate its understanding of the requested change and confirm with the user before applying it to the database.
- No silent writes: every create/update/delete is confirmed first.

### 3.4 Querying Past Data via Chat
- User can ask natural-language questions about past logs, e.g. "what did I eat two days ago?" or "how many macros did I have last Tuesday?"
- The LLM should be able to query the database for the relevant date range and summarize the results conversationally.

### 3.5 Dashboard
- Shows daily summary: calories/macros consumed vs. daily target/budget, ideally consumed and remaining.
- Toggle between Daily / Weekly / Monthly views of progress and trends (e.g. average intake, adherence to targets over time).
- No hourly granularity needed.

## 4. LLM Behavior Requirements
- LLM must output structured data (JSON) for parsed ingredients: ingredient name, quantity, unit, estimated calories, protein (g), carbs (g), fat (g).
- LLM must distinguish between confident estimates and genuinely ambiguous input requiring a follow-up question.
- LLM must never write to the database directly without an explicit user confirmation step in the conversation.
- No confidence score/indicator on estimates is required for this version - use best judgment on presentation; can be added later.

## 5. Suggested Technical Architecture

### 5.1 Stack
- Backend: Python, FastAPI (aligns with existing Python background)
- Frontend: Simple web app - a chat interface + dashboard. Suggest a lightweight framework such as React (or server-rendered templates with FastAPI + Jinja2 if wanting to minimize frontend complexity for V1) with a REST or WebSocket connection to the backend for the chat.
- Database: Start with SQLite for simplicity (single user, no server setup); design schema so migration to PostgreSQL later is straightforward (use an ORM such as SQLAlchemy to keep this portable).
- LLM: Call an existing hosted LLM API directly (e.g. Claude or GPT-4) with a structured prompt/response format (e.g. requesting strict JSON output, or using tool/function calling if the API supports it) rather than fine-tuning or self-hosting a model. This can evolve later (RAG with a nutrition database, local models, etc.) but is explicitly out of scope for V1.
- Auth: Simple username/password login (single user for now, but build as a standard auth flow - hashed passwords, session or JWT-based auth - so it generalizes if ever extended to multiple users).

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
- users: id, username, hashed_password, height, weight, goal_type, activity_level, created_at
- user_targets: id, user_id, daily_calorie_target, protein_target_g, carbs_target_g, fat_target_g, effective_date (to allow target history if recalculated over time)
- log_entries: id, user_id, timestamp, meal_type (inferred), raw_user_message, status (confirmed/pending)
- log_entry_items: id, log_entry_id, ingredient_name, quantity, unit, calories, protein_g, carbs_g, fat_g
- chat_messages: id, user_id, role (user/assistant), content, timestamp, related_log_entry_id (nullable) - for conversational history/context

### 5.4 Deployment (suggested, keep simple for V1)
- Local development first (run FastAPI + SQLite locally).
- When ready to deploy: a simple platform such as Render, Railway, or Fly.io for the backend, with the frontend either served from the same app or deployed separately (e.g. Vercel/Netlify if using React). No need for complex cloud infrastructure (Kubernetes, etc.) at this stage.

## 6. Explicit Scope Boundaries (V1)
Include:
- Chat-based food logging with LLM parsing and macro/calorie estimation
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
