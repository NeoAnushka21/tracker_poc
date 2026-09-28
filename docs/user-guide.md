# OmniAI user guide

OmniAI is a chat-based calorie and macro tracker. In the Chat you talk to **MacBro** (macro + bro), its nutrition assistant: you tell it what you ate in plain words, it works out the calories, protein, carbs, fat, fiber and micronutrients, and **nothing is saved until you confirm it**.

This guide walks a new user through the app from sign-up to daily use. The same walkthrough appears inside the app as a short tour the first time you log in. You can reopen it any time with the **? Guide** button at the top.

> Last updated: 2026-09-28 (chat per day, date picker). Keep this file in step with the UI (see [docs/README.md](README.md)).

---

## Contents

1. [Create your account](#1-create-your-account)
2. [Set up your profile](#2-set-up-your-profile)
3. [The first-run tour](#3-the-first-run-tour)
4. [Your Home page](#4-your-home-page)
5. [Log food in the Chat](#5-log-food-in-the-chat)
6. [Confirm, correct or cancel](#6-confirm-correct-or-cancel)
7. [Edit, move, copy and delete](#7-edit-move-copy-and-delete)
8. [Water](#8-water)
9. [Recipes and My foods](#9-recipes-and-my-foods)
10. [Ask about your history](#10-ask-about-your-history)
11. [The Dashboard](#11-the-dashboard)
12. [Analysis](#12-analysis)
13. [Settings](#13-settings)
14. [Tips for accurate logging](#14-tips-for-accurate-logging)
15. [Troubleshooting and FAQ](#15-troubleshooting-and-faq)

---

## 1. Create your account

1. Open the app and choose **Create account**.
2. Enter your email and a password (at least 8 characters).
3. Tick the **data-use consent** box. By creating an account you agree that the data you share is used for your recommendations and to develop the app.
4. Press **Create account**.

Next time, use **Log in** with the same email and password.

If the consent wording changes later, you'll see a **Before we continue** screen once. Choose **Agree and continue**, or **Log out instead**.

> The **Admin login** link is for the app's administrators only. Normal accounts can't use it.

## 2. Set up your profile

OmniAI needs a few details to work out your daily targets:

| Field | Notes |
|---|---|
| What should I call you? | Optional. Used in the Home greeting and by MacBro in the chat. |
| Date of birth, sex | Used in the calorie formula and for micronutrient reference values. |
| Units | Metric (kg, cm) or Imperial (lb, ft/in). |
| Height, weight | Required. |
| Goal | Lose weight, Build muscle, Gain weight, Recomposition, or Maintain weight. |
| Activity level | From *Sedentary* to *Very active*. |
| Time zone | Detected automatically. It decides where "today" starts and ends. |

After you submit, **Your daily targets** shows the calories, protein, carbs, fat and fiber OmniAI suggests. Change any number you like, then continue. You can change them later in **Settings → Targets**.

<details>
<summary>How targets are calculated</summary>

- **BMR** comes from the Mifflin-St Jeor formula. It's multiplied by your activity factor (1.2 to 1.9) to give **TDEE**.
- **Calories:** TDEE × a goal factor. That's −20% for weight loss, −10% for recomposition, +10% for muscle or weight gain, and ±0% for maintenance.
- **Protein:** 1.8 to 2.2 g per kg of body weight, depending on goal.
- **Fat:** 25% of calories. **Carbs** fill the rest.
- **Fiber:** 14 g per 1,000 kcal.
- **Water:** 35 ml per kg, plus 0 to 1,000 ml for activity.

</details>

## 3. The first-run tour

The first time you reach the main screen, a small panel opens at the bottom. It steps through the tabs (Home → Chat → Dashboard → Analysis → My foods) and explains each one.

- Use **Next** and **Back** (or the ← → keys) to move between steps.
- **Skip**, **✕** or **Esc** closes the tour.
- Reopen it any time from **? Guide** in the top bar.

## 4. Your Home page

**Home** is the first tab you see after logging in.

- **Greeting:** "Good morning", "Good afternoon" or "Good evening" with your name, today's date, and a one-line status (e.g. "979 kcal in, 681 kcal to go").
- **Log a meal** takes you straight to the Chat.
- **Today's summary:** the calorie ring (**eaten / target**, with **Balance** and **Progress**), then protein, fiber, carbs and fat bars, then **Water** with +250 ml / +500 ml / Undo. **Open dashboard →** shows the full day, including meals and micronutrients.
- **Streaks:**

| Streak | Counts |
|---|---|
| **Meal logging streak** 🔥 | Days in a row with at least one confirmed meal |
| **Target streak** 🎯 | Days in a row within ±10% of your calorie target with at least 90% of your protein target |

Each card shows the current streak, your best streak, and the last 7 days as ticks. Today is still in progress, so it never breaks a streak. It is added as soon as it qualifies ("Today counts ✓"); otherwise the card nudges you, e.g. "Log a meal today to keep it going". A day is judged on its final numbers, so the target streak can drop back if you go well over your calories later in the day.

## 5. Log food in the Chat

The **Chat** tab is where you talk to MacBro.

- **Type** what you ate and press **Enter** (Shift+Enter adds a new line), or press **Send**.
- **Speak:** tap the **mic** button, talk, and tap it again when you're done. This needs a browser with speech recognition, such as Chrome or Edge.
- On an empty chat, tap one of the **example chips** to try it out.

Examples:

- `2 eggs and a slice of whole-wheat toast for breakfast`
- `150g grilled chicken, 1 cup cooked rice and a spoon of ghee`
- `a Starbucks tall latte with oat milk`
- `had 3 chapatis and dal for dinner yesterday`

MacBro works out the **meal** from your local time:

| Meal | Time |
|---|---|
| Breakfast | 05:00–10:00 |
| Morning snack | 10:00–12:00 |
| Lunch | 12:00–15:00 |
| Evening snack | 15:00–19:00 (and late night, 23:00–05:00) |
| Dinner | 19:00–23:00 |

Say "for lunch" (or any meal) to override this. Say "yesterday" or give a date to log for another day.

If something is ambiguous, for example "a bowl of pasta", MacBro asks a short question before estimating.

**Stop:** while MacBro is thinking, press **■ Stop**. Your message comes back to the input box so you can edit it and send again.

**Opening the chat** always takes you to the latest message. **Each day starts with a fresh chat.** To see an earlier day's conversation, scroll to the top and tap **Show earlier chat (…)**. It loads the previous day that has messages, and you can keep tapping to go further back. Cards in earlier chats still work.

**Log or change food for another day:** above the message box, **📅 Logging for Today** has a date picker. Pick any past date and everything you type is about that day: new food is logged on it, and edits, moves and deletes look at that day's meals first. Your message shows a small **"for Yesterday"** / **"for Fri, 25 Sep"** tag. Press **Back to today** when you're done. You can also just say the day in your message ("add 2 eggs to Monday's breakfast").

Today's totals are on the **Home** tab (and in the **Day so far** card after each confirmed meal).

## 6. Confirm, correct or cancel

Every change MacBro suggests arrives as a **card** marked **Not saved yet**. It lists each item with its quantity, calories and protein / carbs / fat, then the totals, meal and time.

| Button | What it does |
|---|---|
| **Looks good** | Saves it. Depending on the change, this button reads *Yes, delete*, *Move it*, *Copy it*, *Log water* or *Save recipe* instead. |
| **Needs changes** | Tell MacBro what to fix, e.g. "the rice was 200g", "it was lunch, not dinner". A new card replaces the old one, which is marked superseded. |
| **Cancel** | Throws the suggestion away. Nothing is saved. |

After you confirm a meal, a **Day so far** card shows how much of each target you've used and what's left, with a short encouraging message.

Cards you leave unanswered expire after 24 hours. Unconfirmed cards never count toward your totals.

## 7. Edit, move, copy and delete

You can do this **in the chat** (with a confirmation card) or **on the Dashboard** (straight away).

**In the chat:**

- `make the rice 150g` / `the chicken was actually 200g`
- `remove the cookie from my evening snack`
- `move the banana to morning snack`: a *Move* card shows *from → to*, and nothing is deleted.
- `copy yesterday's breakfast to today`

**On the Dashboard:** **+ Log food** (next to *Meals*) opens the chat set to the day you're viewing, which is handy for filling in a past day. For a single item, tap the **pencil** ✎ next to any item in a meal. A small panel opens:

- **Move / Copy:** pick **Move** or **Copy**, choose the meal from the dropdown, and press the **→** button. Move lists only the other meals. When you're looking at a past day, Copy adds the item to *today's* meal.
- **Quantity:** change the amount and press the **✓** button. Nutrients scale automatically.
- Icon buttons on the right (hover for a label):
  - **speech bubble**: edit in chat. It opens the chat with the message started for you and set to that item's day, e.g. to change ingredients.
  - **trash can**: delete. It asks you to confirm first.
  - **✕**: close the panel.

## 8. Water

- **Chat:** `two glasses of water`, `drank 750 ml`. You'll get a water card; press **Log water**.
- **Dashboard:** in the **Water** section, tap **+ 250 ml** or **+ 500 ml**, or **Undo** to remove the last entry.

Your water target is based on your weight and activity level. The bar shows litres drunk against the target, with "to go" or "goal met ✓".

## 9. Recipes and My foods

**My foods** is your personal food library. Every food in a meal you confirm is saved there automatically, so the next time you log it MacBro reuses **exactly the same numbers** and scales them to the amount.

- **Search** by name or brand, and filter by **All / Foods / Recipes**.
- Each food is a card showing its **calories in bold** and coloured chips for **P**rotein, **C**arbs, **F**at and **Fiber**.
- **Edit** (pencil icon) a food to fix its values (per 100 g/ml, or per piece/serving with the gram weight). Foods you edit by hand are never overwritten by later estimates.
- **Delete** (trash icon) a food you no longer want. With a mouse, the icons appear when you hover over a card; on touch screens they're always visible. Past logs keep their numbers.

**Recipes** are for dishes you make at home:

1. In the chat, say `save my chapati as a recipe` (MacBro may also offer this for dishes you log often).
2. Give the raw ingredients for the whole batch and what it makes, e.g. `200g multigrain atta, 10ml oil, makes 8 chapatis`.
3. Check the recipe card and press **Save recipe**.
4. From then on, `had 3 chapatis` uses the recipe's per-piece values.

Editing a recipe only affects future logs.

## 10. Ask about your history

MacBro answers from your **confirmed** data only:

- `what did I eat yesterday?`
- `how much protein did I have this week?`
- `what was my highest-calorie meal on Monday?`
- `how many calories do I have left today?`

## 11. The Dashboard

| Section | What you see |
|---|---|
| **Day navigation** | **‹ ›** to move between days (not into the future). |
| **Calorie ring** | Calories **eaten / target**. Beside it: **Balance** (calories left) or **Over budget by**, and **Progress %**. |
| **Macro bars** | Thick bars for Protein (green), Fiber (magenta), Carbs (amber) and Fat (cyan), with current / target above each bar. |
| **Where today's calories came from** | A split bar of protein, carbs and fat calories (hover for numbers). |
| **Water** | Litres against target, quick-add buttons, undo. |
| **Additional micronutrients** | Iron, calcium, magnesium, potassium, zinc, vitamin C, vitamin B12 and vitamin D, against daily reference values for your age and sex. Sodium is shown as a limit to stay under. |
| **Meals** | Breakfast, Morning snack, Lunch, Evening snack and Dinner, each with its own calories and macros. Tap a meal to expand it and the **pencil** on an item to move, copy, change or delete it. |

Micronutrients are estimates. Treat them as a guide, not a lab result.

## 12. Analysis

The **Analysis** tab shows trends over **7, 14 or 30 days**:

- summary cards: average calories, average protein, average water (your target streak is on **Home**)
- calories per day and protein per day against target
- macro trends
- where your calories came from
- calories by meal
- water per day
- a data table under each chart

Hover over any chart, or tab to it with the keyboard, to see exact values. A day counts as "on target" when calories are within ±10% of target and protein is at least 90% of target.

## 13. Settings

Open **⚙ Settings** from the top bar.

| Tab | What you can do |
|---|---|
| **Account** | See your email, registration date, last login, when you gave data consent, your goal and time zone. Switch the **Appearance** between light, dark or system. |
| **Targets** | Edit daily calories, protein, carbs, fat and fiber. |
| **Body profile** | See current weight (with change since last time) and height, and save new values. Tick *Recalculate my targets* if you want targets updated. Add optional **body measurements** (neck, chest, waist, hips, biceps, forearm, thigh, calf). Each save is dated so you can track change, and entries can be deleted from the history. |
| **Password** | Change your password (needs the current one). |
| **Delete account** | Permanently removes your account and **all** your data. Needs your password and can't be undone. |

## 14. Tips for accurate logging

- **Give amounts:** grams, cups, pieces or "a medium bowl". Weighed amounts are the most accurate.
- **Mention oil, butter, ghee and sauces.** They add a lot of calories.
- **Say whether amounts are cooked or raw** for rice, pasta and meat.
- **Name brands** for packaged foods. If MacBro doesn't know a product, it asks you for the label values.
- **Save recipes** for home-cooked dishes you eat often.
- **Correct once, reuse forever:** fix a food in *My foods* and every future log uses your numbers.

## 15. Troubleshooting and FAQ

**"MacBro's servers are temporarily down."** The AI model is unavailable or its free daily limit is used up. Your data is safe. Try again later. You can still use the Dashboard, water buttons and item actions, since they don't need the AI.

**The mic button is missing.** Your browser doesn't support speech recognition. Use Chrome or Edge, or type instead.

**I confirmed the wrong thing.** Fix it on the Dashboard with the **pencil** on that item, or ask in the chat, e.g. "delete the pizza from lunch".

**The meal was put in the wrong slot.** Move it with **pencil → Move → pick the meal → →**, or say "move it to lunch".

**Why didn't MacBro say "logged"?** MacBro never saves anything on its own. Only your button press saves.

**Can other users see my data?** No. Administrators can view account data read-only for support and development, as described in the consent notice, and every admin view is recorded in an audit log.
