# MacBro user guide

MacBro (macro + bro) is a chat-based calorie and macro tracker. You tell it what you ate in plain words, it works out the calories, protein, carbs, fat, fiber and micronutrients, and **nothing is saved until you confirm it**.

This guide walks a new user through the app from sign-up to daily use. The same walkthrough appears inside the app as a short tour the first time you log in. You can reopen it any time with the **? Guide** button at the top.

> Last updated: 2026-09-28. Keep this file in step with the UI (see [docs/README.md](README.md)).

---

## Contents

1. [Create your account](#1-create-your-account)
2. [Set up your profile](#2-set-up-your-profile)
3. [The first-run tour](#3-the-first-run-tour)
4. [Log food in the Chat](#4-log-food-in-the-chat)
5. [Confirm, correct or cancel](#5-confirm-correct-or-cancel)
6. [Edit, move, copy and delete](#6-edit-move-copy-and-delete)
7. [Water](#7-water)
8. [Recipes and My foods](#8-recipes-and-my-foods)
9. [Ask about your history](#9-ask-about-your-history)
10. [The Dashboard](#10-the-dashboard)
11. [Analysis](#11-analysis)
12. [Settings](#12-settings)
13. [Tips for accurate logging](#13-tips-for-accurate-logging)
14. [Troubleshooting and FAQ](#14-troubleshooting-and-faq)

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

MacBro needs a few details to work out your daily targets:

| Field | Notes |
|---|---|
| What should I call you? | Optional. MacBro uses it in greetings. |
| Date of birth, sex | Used in the calorie formula and for micronutrient reference values. |
| Units | Metric (kg, cm) or Imperial (lb, ft/in). |
| Height, weight | Required. |
| Goal | Lose weight, Build muscle, Gain weight, Recomposition, or Maintain weight. |
| Activity level | From *Sedentary* to *Very active*. |
| Time zone | Detected automatically. It decides where "today" starts and ends. |

After you submit, **Your daily targets** shows the calories, protein, carbs, fat and fiber MacBro suggests. Change any number you like, then continue. You can change them later in **Settings → Targets**.

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

The first time you reach the main screen, a small panel opens at the bottom. It steps through the tabs (Chat → Dashboard → Analysis → My foods) and explains each one.

- Use **Next** and **Back** (or the ← → keys) to move between steps.
- **Skip**, **✕** or **Esc** closes the tour.
- Reopen it any time from **? Guide** in the top bar.

## 4. Log food in the Chat

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

Above the chat, the **summary strip** shows today's calories as **eaten / target** (e.g. `1,005 / 1,920 kcal today`) with protein, carbs and fat. Click it to open the Dashboard.

## 5. Confirm, correct or cancel

Every change MacBro suggests arrives as a **card** marked **Not saved yet**. It lists each item with its quantity, calories and protein / carbs / fat, then the totals, meal and time.

| Button | What it does |
|---|---|
| **Looks good** | Saves it. Depending on the change, this button reads *Yes, delete*, *Move it*, *Copy it*, *Log water* or *Save recipe* instead. |
| **Needs changes** | Tell MacBro what to fix, e.g. "the rice was 200g", "it was lunch, not dinner". A new card replaces the old one, which is marked superseded. |
| **Cancel** | Throws the suggestion away. Nothing is saved. |

After you confirm a meal, a **Day so far** card shows how much of each target you've used and what's left, with a short encouraging message.

Cards you leave unanswered expire after 24 hours. Unconfirmed cards never count toward your totals.

## 6. Edit, move, copy and delete

You can do this **in the chat** (with a confirmation card) or **on the Dashboard** (straight away).

**In the chat:**

- `make the rice 150g` / `the chicken was actually 200g`
- `remove the cookie from my evening snack`
- `move the banana to morning snack`: a *Move* card shows *from → to*, and nothing is deleted.
- `copy yesterday's breakfast to today`

**On the Dashboard:** tap **⋯** next to any item in a meal:

- **Move to**: pick another meal.
- **Copy to** (or **Copy to today's** when looking at a past day): duplicates the item.
- **Quantity**: change the amount and press **Save**. Nutrients scale automatically.
- **✎ Ask MacBro to edit**: opens the chat with the message started for you, e.g. to change ingredients.
- **Delete**: asks you to confirm first.

## 7. Water

- **Chat:** `two glasses of water`, `drank 750 ml`. You'll get a water card; press **Log water**.
- **Dashboard:** in the **Water** section, tap **+ 250 ml** or **+ 500 ml**, or **Undo** to remove the last entry.

Your water target is based on your weight and activity level. The bar shows litres drunk against the target, with "to go" or "goal met ✓".

## 8. Recipes and My foods

**My foods** is your personal food library. Every food in a meal you confirm is saved there automatically, so the next time you log it MacBro reuses **exactly the same numbers** and scales them to the amount.

- **Search** by name or brand, and filter by **All / Foods / Recipes**.
- **Edit** a food to fix its values (per 100 g/ml, or per piece/serving with the gram weight). Foods you edit by hand are never overwritten by later estimates.
- **Delete** a food you no longer want. Past logs keep their numbers.

**Recipes** are for dishes you make at home:

1. In the chat, say `save my chapati as a recipe` (MacBro may also offer this for dishes you log often).
2. Give the raw ingredients for the whole batch and what it makes, e.g. `200g multigrain atta, 10ml oil, makes 8 chapatis`.
3. Check the recipe card and press **Save recipe**.
4. From then on, `had 3 chapatis` uses the recipe's per-piece values.

Editing a recipe only affects future logs.

## 9. Ask about your history

MacBro answers from your **confirmed** data only:

- `what did I eat yesterday?`
- `how much protein did I have this week?`
- `what was my highest-calorie meal on Monday?`
- `how many calories do I have left today?`

## 10. The Dashboard

| Section | What you see |
|---|---|
| **Day navigation** | **‹ ›** to move between days (not into the future). |
| **Calorie ring** | Calories **eaten / target**. Beside it: **Balance** (calories left) or **Over budget by**, and **Progress %**. |
| **Macro bars** | Protein, Fiber, Carbs and Fat against target. |
| **Where today's calories came from** | A split bar of protein, carbs and fat calories (hover for numbers). |
| **Water** | Litres against target, quick-add buttons, undo. |
| **Additional micronutrients** | Iron, calcium, magnesium, potassium, zinc, vitamin C, vitamin B12 and vitamin D, against daily reference values for your age and sex. Sodium is shown as a limit to stay under. |
| **Meals** | Breakfast, Morning snack, Lunch, Evening snack and Dinner, each with its own calories and macros. Tap a meal to expand it and **⋯** on an item for actions. |

Micronutrients are estimates. Treat them as a guide, not a lab result.

## 11. Analysis

The **Analysis** tab shows trends over **7, 14 or 30 days**:

- summary tiles: average calories, average protein, **days on target**, average water
- calories per day and protein per day against target
- macro trends
- where your calories came from
- calories by meal
- water per day
- a data table under each chart

Hover over any chart, or tab to it with the keyboard, to see exact values. A day counts as "on target" when calories are within ±10% of target and protein is at least 90% of target.

## 12. Settings

Open **⚙ Settings** from the top bar.

| Tab | What you can do |
|---|---|
| **Account** | See your email, registration date, last login, when you gave data consent, your goal and time zone. Switch the **Appearance** between light, dark or system. |
| **Targets** | Edit daily calories, protein, carbs, fat and fiber. |
| **Body profile** | See current weight (with change since last time) and height, and save new values. Tick *Recalculate my targets* if you want targets updated. Add optional **body measurements** (neck, chest, waist, hips, biceps, forearm, thigh, calf). Each save is dated so you can track change, and entries can be deleted from the history. |
| **Password** | Change your password (needs the current one). |
| **Delete account** | Permanently removes your account and **all** your data. Needs your password and can't be undone. |

## 13. Tips for accurate logging

- **Give amounts:** grams, cups, pieces or "a medium bowl". Weighed amounts are the most accurate.
- **Mention oil, butter, ghee and sauces.** They add a lot of calories.
- **Say whether amounts are cooked or raw** for rice, pasta and meat.
- **Name brands** for packaged foods. If MacBro doesn't know a product, it asks you for the label values.
- **Save recipes** for home-cooked dishes you eat often.
- **Correct once, reuse forever:** fix a food in *My foods* and every future log uses your numbers.

## 14. Troubleshooting and FAQ

**"MacBro's servers are temporarily down."** The AI model is unavailable or its free daily limit is used up. Your data is safe. Try again later. You can still use the Dashboard, water buttons and item actions, since they don't need the AI.

**The mic button is missing.** Your browser doesn't support speech recognition. Use Chrome or Edge, or type instead.

**I confirmed the wrong thing.** Fix it on the Dashboard with **⋯**, or ask in the chat, e.g. "delete the pizza from lunch".

**The meal was put in the wrong slot.** Move it with **⋯ → Move to**, or say "move it to lunch".

**Why didn't MacBro say "logged"?** MacBro never saves anything on its own. Only your button press saves.

**Can other users see my data?** No. Administrators can view account data read-only for support and development, as described in the consent notice, and every admin view is recorded in an audit log.
