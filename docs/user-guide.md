# OmniAI user guide

OmniAI is a chat-based calorie and macro tracker. In the Chat you talk to **MacBro** (macro + bro), its nutrition assistant: you tell it what you ate in plain words, it works out the calories, protein, carbs, fat, fiber and micronutrients, and **nothing is saved until you confirm it**.

This guide walks a new user through the app from sign-up to daily use. The same walkthrough appears inside the app as a short tour the first time you log in. You can reopen it any time with the **? Guide** button at the top.

> Last updated: 2026-09-30 (**+ Add** in Saved Food: a branded product, a generic food or a recipe from a form; branded foods: a **Brands** filter in Saved Food, and **Check label** fetches the real pack label from Open Food Facts; Settings reorganised: About you, Targets, Appearance, Account & privacy, Security; India only for now in the country list; optional "About you" questions: diet, allergies, pace, meal times, training, health; country and region in the profile, age in Settings; built-in general food list of ~300 common foods (USDA) used without the AI; "raw or cooked?" asked, never assumed; small typos in saved-food names and meal words are understood without the AI; Dashboard asks "Did you mean …?"; earlier: Saved Food renamed Saved Food, a list with Additional info; Body renamed Body Profile; new Explore tab, coming soon; terms page; earlier: health notes and low-target warning, forgot password…). Keep this file in step with the UI (see [docs/README.md](README.md)).

---

## Contents

- [Opening OmniAI](#opening-omniai)
1. [Create your account](#1-create-your-account)
2. [Set up your profile](#2-set-up-your-profile)
3. [The first-run tour](#3-the-first-run-tour)
4. [Your Home page](#4-your-home-page)
5. [Log food in the Chat](#5-log-food-in-the-chat)
6. [Confirm, correct or cancel](#6-confirm-correct-or-cancel)
7. [Edit, move, copy and delete](#7-edit-move-copy-and-delete)
8. [Water](#8-water)
9. [Recipes and Saved Food](#9-recipes-and-saved-food)
10. [Ask about your history](#10-ask-about-your-history)
11. [The Dashboard](#11-the-dashboard)
12. [Analysis](#12-analysis)
13. [Explore](#13-explore)
14. [Body Profile](#14-body-profile)
15. [Settings](#15-settings)
16. [Tips for accurate logging](#16-tips-for-accurate-logging)
17. [Troubleshooting and FAQ](#17-troubleshooting-and-faq)

---

## Opening OmniAI

Open **https://omniai-app.onrender.com** (bookmark it). The app runs on a free server that naps when nobody has used it for about 15 minutes. If it's napping, you'll see **MacBro dancing** with messages like "MacBro is warming up the kitchen…" for up to a minute, then the app opens by itself. If it's awake, the app opens straight away.

The same screen can appear briefly while you're using the app if it was left open long enough for the server to nap. Just wait; your action carries on by itself. If it takes more than about 3 minutes, tap **Try again**.

## 1. Create your account

1. Open the app and choose **Create account**.
2. Enter your email and a password (at least 8 characters).
3. Tick the **data-use consent** box. By creating an account you agree that the data you share is used for your recommendations and to develop the app, and that your chat messages (with related context such as your targets and today's logs) are processed by third-party AI services running open-source models.
4. Press **Create account**.

Next time, use **Log in** with the same email and password.

**Or continue with Google.** Under the form, **Continue with Google** signs you in with your Google account instead of a password. Choose whichever you like:

- **New to OmniAI:** Google asks which account to use, then OmniAI shows the data-use consent. Tick it and press **Create account**. Your first name from Google fills in "What should I call you?" (you can change it).
- **You already have an email + password account with the same email:** OmniAI asks **Link your Google account?** first. Press **Link and continue** to use either Google or your password from then on, or **Cancel** to leave your account as it is. Nothing is linked without your OK.
- **Next time:** press **Continue with Google** again; there's no password to remember.

If you signed up with Google, you have no password yet. Logging in with email and password tells you to use Google instead; you can set a password in **Settings → Set password**.

**Forgot your password?** On **Log in**, tap **Forgot password?**, enter your email and press **Send reset link**. If an account exists, you'll get an email with a link (check spam too). It works **once, for 30 minutes**: open it, choose a new password, then log in. Setting a new password this way signs you out on every device. You can ask for up to 3 links an hour; each new one replaces the last. Accounts made with Google can use this to set a password too. (The link only appears once the app can send emails.)

If the consent wording changes later (it did on 2026-09-28, to mention the AI services), you'll see a **Before we continue** screen once. Choose **Agree and continue**, or **Log out instead**.

> The **Admin login** link is for the app's administrators only. Normal accounts can't use it.

**Terms:** the **Terms** link (also at **/terms**) sets out the basics in plain words: adults only, estimates not medical advice, fair use of the free AI, your data stays yours, and the app is provided free and as is.

**Privacy:** the **Privacy** link under the sign-in form (also at **/privacy**, no login needed) explains in plain words what OmniAI stores, why, which services handle it (Render and Neon in Singapore, Groq in the US for the AI, Google if you use it, Open Food Facts for label searches), how long it's kept, and how to download or delete it. OmniAI is for adults (18 and over).

## 2. Set up your profile

OmniAI needs a few details to work out your daily targets:

| Field | Notes |
|---|---|
| What should I call you? | Optional. Used in the Home greeting and by MacBro in the chat. |
| Date of birth, sex | Used in the calorie formula and for micronutrient reference values; your **age** is worked out from the date of birth (shown in **Settings → About you**). You need to be **18 or over** to use OmniAI; a date of birth under 18 (or in the future) isn't accepted. |
| Country | **Required.** Pick it from the list (you can't type your own). OmniAI is available in **India** for now, so India is the only choice and is already selected; more countries will follow. |
| State / region | Optional. Pick your state or union territory from the list, or leave it as *Not specified*. |
| Units | Metric (kg, cm) or Imperial (lb, ft/in). |
| Height, weight | Required. |
| Goal | Lose weight, Build muscle, Gain weight, Recomposition, or Maintain weight. |
| Activity level | From *Sedentary* to *Very active*. |
| Time zone | Detected automatically. It decides where "today" starts and ends. |

**A bit more about you (optional).** After the required details, OmniAI offers a few optional questions. Answer any of them, or press **Skip for now**; everything can be filled in or changed later in **Settings → About you**. Each answer is used:

| Question | What it changes |
|---|---|
| Diet (vegetarian, eggetarian, non-vegetarian, vegan, Jain) | MacBro suggests foods that fit it |
| Allergies or intolerances (pick from the list, plus "anything else") | Cards say **Heads-up** when a food usually contains one, e.g. "curd usually contains milk / dairy" |
| How fast? (weight loss 0.25–1 kg a week; gain 0.25–0.5 kg) | Your calorie target: about 1,100 kcal a day per kg a week, below or above maintenance. A loss is never set more than 25% below maintenance. |
| Usual breakfast, lunch and dinner times | Which meal a message counts as (with breakfast at 10:30, food at noon is breakfast), and the time used when you add food to an empty meal on the Dashboard |
| Training (type and days) | MacBro knows when you train |
| **Health** (optional, sensitive): conditions such as diabetes, PCOS or thyroid, and for a female profile pregnancy or breastfeeding | Context for MacBro, which still gives no medical advice. While pregnant or breastfeeding, no calorie deficit is set. Saving these needs an extra tick: you agree they're used only for this. Clearing them removes that agreement too. |

If your answers change the calculated calories (a pace, or pregnancy), you see the new targets before starting; later, in Settings, OmniAI asks **Use the new target** or **Keep mine**.

**Already had an account?** If you joined before country and region were added, OmniAI asks once after you sign in: **Where do you live?** Pick your country (required) and region (optional), then **Save and continue**. You can change both later in **Settings → About you** (**Country / state → Change**). The optional **A bit more about you** questions are offered once too (after the country), with **Skip for now**.

After you submit, **Your daily targets** shows the calories, protein, carbs, fat and fiber OmniAI suggests. Change any number you like, then continue. You can change them later in **Settings → Targets**. If the calorie target is below **1,200 kcal (women) or 1,500 kcal (men)**, a heads-up explains that such low targets are usually only advised with a doctor or dietitian involved. It's a warning, not a block.

> OmniAI's calories, nutrients, targets, BMI and body-fat numbers are **estimates to help you track, not medical advice** (a reminder sits at the bottom of Home and the Dashboard). Talk to a doctor or dietitian about medical conditions, pregnancy or big changes to how you eat.

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

The first time you reach the main screen, a small panel opens at the bottom. It steps through the tabs (Home → Chat → Dashboard → Analysis → Saved Food → Explore → Body Profile) and explains each one.

- Use **Next** and **Back** (or the ← → keys) to move between steps.
- **Skip**, **✕** or **Esc** closes the tour.
- Reopen it any time from **? Guide** in the top bar.

**Phone or laptop:** the app works on both, with the same tabs at the top. On a phone, each page is one column you scroll through. On a laptop or any window at least 1024 px wide, the pages use the extra space:

| Page | On a laptop |
|---|---|
| Home | Today's summary (macros) on the left; the Water tile and the two streaks stacked on the right |
| Chat | Wider conversation; messages keep a comfortable reading width |
| Dashboard | The macros, micronutrients and water tiles on the left, your **meals** on the right |
| Analysis | Charts in two columns: calories beside protein, macro trends beside water, the calorie split beside calories by meal |
| Saved Food | A full-width list: name and calories on each line, the details opening underneath |
| Explore | Recipe collection tiles in rows of up to four |
| Body Profile | The body diagram with labelled arrows on both sides and the measurement editor beside it (on a phone: numbered dots and a list) |

On very wide screens, content stays at a comfortable width (about 1,200 px) in the middle, lined up with the top bar.

## 4. Your Home page

**Home** is the first tab you see after logging in.

- **Greeting:** "Good morning", "Good afternoon" or "Good evening" with your name, today's date, and a one-line status (e.g. "979 kcal in, 681 kcal to go").
- **Log a meal** takes you straight to the Chat.
- **Today's summary** tile: the calorie ring (**eaten / target**, with **Balance** and **Progress**), then protein, fiber, carbs and fat bars. **Open dashboard →** shows the full day, including meals and micronutrients.
- **Water** tile, separate from the macros: litres against your goal with +250 ml / +500 ml / Undo.
- **Streaks:**

| Streak | Counts |
|---|---|
| **Meal logging streak** 🔥 | Days in a row with at least one confirmed meal |
| **Protein streak** 🏋️ | Days in a row where you reached at least **85% of your protein target**. Calories don't affect it. |

Each card shows the current streak, your best streak, and the last 7 days as ticks. Today is still in progress, so it never breaks a streak. It is added as soon as it qualifies ("Today counts ✓"); otherwise the card nudges you, e.g. "Log a meal today to keep it going". The moment a streak is completed for today, its card pops once when you next open Home. A day is judged on its final numbers: once today reaches 85% of your protein it counts, and it only drops back if you delete or reduce food later that day.

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

**While MacBro is thinking** he nods along with little maths symbols floating up, and a line such as "Doing the maths…" changes every couple of seconds.

**Stop:** while MacBro is thinking, press **■ Stop**. Your message comes back to the input box so you can edit it and send again.

**Opening the chat** always takes you to the latest message. **Each day starts with a fresh chat.** To see an earlier day's conversation, scroll to the top and tap **Show earlier chat (…)**. It loads the previous day that has messages, and you can keep tapping to go further back. Cards in earlier chats still work.

**Log or change food for another day:** above the message box, **📅 Logging for Today** has a date picker. Pick any past date and everything you type is about that day: new food is logged on it, and edits, moves and deletes look at that day's meals first. Your message shows a small **"for Yesterday"** / **"for Fri, 25 Sep"** tag. Press **Back to today** when you're done. You can also just say the day in your message ("add 2 eggs to Monday's breakfast").

**Daily AI messages:** OmniAI runs on a free AI service shared by everyone, so each account gets **20 AI messages a day** (the number may change). The count left is shown above the message box, e.g. "14 of 20 AI messages left today", and it resets at midnight in your time zone.

- **Counts:** a message the AI answers, and a new food estimated on the Dashboard (**+ Add food**).
- **Doesn't count:** instant replies (a water amount, "what's left today", foods all in Saved Food or the general food list, the raw/cooked question and your answer, "same breakfast as yesterday"), saved and general-list foods added on the Dashboard, every button (Looks good, water, move, delete…), and messages that fail or that you stop.
- When they're used up, your message stays in the box with a note. Everything that doesn't need the AI keeps working.

Today's totals are on the **Home** tab (and in the summary card after each confirmed log: macros after food, water after water).

## 6. Confirm, correct or cancel

Every change MacBro suggests arrives as a **card** marked **Not saved yet**; new cards pop in with a small bounce. A food card leads with the bottom line: **calories** and **protein** in large numbers. Below them is a short, dimmed list of what MacBro understood (each item and its amount), so you can check it at a glance. Tap **View details** for the full breakdown: each item's calories, protein, carbs and fat, plus the totals with fiber. Recipe cards work the same way, with the numbers per piece or serving.

| Button | What it does |
|---|---|
| **Looks good** | Saves it. Depending on the change, this button reads *Yes, delete*, *Move it*, *Copy it*, *Log water* or *Save recipe* instead. On a phone it gets its own full-width row. |
| **Needs changes** | Tell MacBro what to fix, e.g. "the rice was 200g", "it was lunch, not dinner". A new card replaces the old one, which is marked superseded. |
| **Cancel** | Throws the suggestion away. Nothing is saved. |

After you confirm, a summary card appears for **the day you logged for** (today, or the day picked under **Logging for**):

- **After food** (or a move, copy, change or delete): **Day so far** (or e.g. **Yesterday total**) shows calories and how much of each macro target you've used and what's left, with a short encouraging message. Its bars fill up as the card appears.
- **After water:** **Water today** (or e.g. **Water · Yesterday**) shows litres against your goal, the percentage, what's left (or "goal met ✓"), and a hydration message. It doesn't repeat the macros.

Cards you leave unanswered expire after 24 hours. Unconfirmed cards never count toward your totals.

**On an Android phone** OmniAI gives a small vibration for key moments: a double pulse when **Looks good** saves, a light tick on the water **+ 250 ml / + 500 ml** buttons, and a longer buzz when a streak is completed for today. iPhones don't allow web apps to vibrate. Vibrations (and the animations) are off if your device is set to **reduce motion**.

## 7. Edit, move, copy and delete

You can do this **in the chat** (with a confirmation card) or **on the Dashboard** (straight away).

**In the chat:**

- `make the rice 150g` / `the chicken was actually 200g`
- `remove the cookie from my evening snack`
- `move the banana to morning snack`: a *Move* card shows *from → to*, and nothing is deleted.
- `copy yesterday's breakfast to today`

**On the Dashboard:** **+ Log food** (next to *Meals*) opens the chat set to the day you're viewing, which is handy for filling in a past day.

**Add a food without the chat:** each meal has **+ Add food**. Type the food (your saved foods are suggested as you type), the quantity and the unit, then press **Add**. It goes into that meal on the day you're viewing.

- **A saved food** (one in Saved Food) is added straight away with your saved numbers. The unit list shows only the units it can be measured in (e.g. g, piece).
- **A small typo of a saved food** (say `panner` for Paneer) asks **Did you mean Paneer?** first, without the AI. **Use Paneer** adds your saved one (if the unit you typed doesn't fit it, pick one from the unit list and press **Add**). **No, add "panner"** treats it as a new food.
- **A common food on the general food list** (see §9), e.g. `banana`, `ghee`, `chicken breast, cooked`, shows a preview marked **General food list · Not saved yet**, without the AI. If it could be raw or cooked (rice, dal, chicken…) and you didn't say, it first asks **raw or cooked?** with two buttons.
- **A new food** is estimated by the AI. You'll see its calories and macros marked **AI estimate · Not saved yet**, with any assumption it made. Press **Add it** to save it (it's also saved to Saved Food, so next time it's instant), **Change** to edit what you typed, or **Cancel**.
- If the AI can't estimate it (for example, it isn't a food), you'll see why, with **Ask in chat instead**.
- An empty meal gets its usual time (breakfast 08:00, morning snack 11:00, lunch 13:00, evening snack 17:00, dinner 20:00, or now if that's later today); a meal that already has food keeps its time.

For a single item that's already logged, tap the **pencil** ✎ next to any item in a meal. A small panel opens:

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

## 9. Recipes and Saved Food

**Saved Food** is your personal food library. Every food in a meal you confirm is saved there automatically, with its calories, macros **and micronutrients**, so the next time you log it MacBro reuses **exactly the same numbers** and scales them to the amount.

**How a repeat food is logged:**

1. The first time you log a new food (say, pineapple), MacBro's AI estimates it. When you confirm, it's saved to Saved Food per 100 g (or per piece or serving), micronutrients included.
2. Later, a simple message like `had 40g pineapple` or `2 eggs for breakfast` is answered **straight from Saved Food, without the AI**. The saved numbers, micronutrients included, are scaled to your amount. The card says "All from your saved foods".
   - **Small typos are fine:** `200g cooked chiken breast` still finds your saved chicken breast, and the card says what it read ("I read 'cooked chiken breast' as chicken breast, cooked"), so you can check before confirming. To avoid wrong guesses, names under 5 letters (egg, oats) must be spelt exactly, longer ones may be off by one letter (two from 9 letters), and if the typo is close to two saved foods the AI handles it instead.
   - **Meal words too:** `brkfst`, `breakfst`, `bekfast`, `bfast`, `lnch`, `dinr`, `snak` or `mornng snak` are read as the meal, when they come after *for*, *at*, *in*, *as*, *my*, *same* or *yesterday's* (e.g. `3 eggs for brkfst`), so "a bunch of grapes" is never read as lunch.
3. The Dashboard's **+ Add food** works the same way: a saved food is added from Saved Food without the AI (a small typo asks "Did you mean …?" first), and a new one is estimated once and saved when you add it.
4. This shortcut needs **an amount for every item** (`40g`, `2`, `1 serving`, `1 tbsp`, `1 cup`) and **every item already saved or on the general food list** (below). A count like `1 apple` also needs the food's **g per piece** (add it in **Edit** if it's missing). Otherwise the message goes to the AI, which still reuses your saved numbers for the foods it recognises.

**The general food list (no AI):** OmniAI also comes with about **300 common foods**: fruits, vegetables, grains and flours, dals and beans, dairy, eggs, meat and fish, nuts and seeds, oils and ghee, sugar, sauces and common drinks. Their numbers per 100 g, micronutrients included, come from **USDA FoodData Central** (a public-domain US government database). Indian names work too (`kela`, `atta`, `toor dal`, `dahi`, `palak`…), as do small typos.

- **Lookup order:** your Saved Food first (your numbers always win), then the general list, then the AI.
- `had 150 g banana and 1 tbsp ghee` makes a card straight from the list, marked "From the general food list … plain food with no oil or salt". Confirm it and the food is copied into Saved Food, so from then on it's yours to edit.
- **Raw or cooked is never assumed.** Meat, chicken, fish, prawns, rice, other grains (oats, quinoa, millet, dalia, pasta, noodles) and dals/beans have very different calories raw and cooked (cooked rice is about 130 kcal per 100 g, raw rice 365). If you give a weight without saying which (`200 g rice`), MacBro asks **"Was the rice weighed raw or cooked?"** with **Raw** / **Cooked** buttons. You can also type the answer, or for two foods `chicken raw, rice cooked`. Saying it upfront (`200 g cooked rice`, `150 g raw chicken breast`, `boiled dal`) skips the question. The same applies to a food you saved as, say, "chicken breast, cooked": typing just `chicken breast` asks, so a raw weight isn't logged with cooked numbers.
- Counted pieces without a weight (`2 chicken drumsticks`) and dishes (`chicken curry`, `dal tadka`, `paneer butter masala`) aren't on the list; the AI handles them as before. Not on the list yet: paneer, poha, jaggery, ragi, idli, dosa and other cooked dishes.

- **Search** by name or brand, and filter by **All / Foods / Recipes / Brands**.
- **+ Add** (top right) adds a food yourself, without the chat. First pick what you're adding, then fill in its form:
  - **Branded product:** brand and product name. **Search Open Food Facts** finds the pack label (by brand and name, or the barcode number) and **Use this** fills in the form; or copy the **nutrition table** from the pack: per 100 g or ml, energy (kcal), protein, carbohydrate, fibre, total fat, sodium, and the serving size. **More nutrients from the label** takes the rest. Keep **These values are from the pack label** ticked when you copied them from the pack, and the food shows **label ✓**. If you change a number after picking a product, your typed numbers are saved instead.
  - **Generic food:** a loose or home food (paneer, a sabzi…): name, the amount the numbers are for (per 100 g, 100 ml, 1 piece or 1 serving), kcal, protein, carbs, fat, and optionally fiber, g per piece, g per serving and micronutrients. Common foods (banana, rice, ghee, dals…) are already on the general food list, so you only need this for foods that aren't, or to use your own numbers.
  - **Recipe:** a name, the **raw ingredients for the whole batch** (each with an amount and unit, e.g. `200 g`, `1 tbsp`), and what it makes (**servings** or **pieces**, and optionally the **cooked weight** of the whole batch, so you can log it in grams). Ingredients come from your Saved Food (suggested as you type) or the general food list; anything else, add first as a generic food or branded product. **Calculate** shows the numbers per serving (or piece, or 100 g) and each ingredient's calories before you save; **Save recipe** saves it. Ingredients from the general list are saved to Saved Food too.
  - If a food's protein, carbs and fat don't add up to roughly its calories, the form says so. It's only a hint (labels round a little); you can still save. A food with the same name (and brand) as one you already have isn't added twice: edit that one instead.
- Foods are shown as a **list**: each line has the food's **name** and its **calories** for the saved amount (e.g. "165 kcal per 100 g").
- Tap **Additional info** on a line to open the rest: **protein, carbs, fat and fiber**, the saved **micronutrients** (iron, calcium, magnesium, potassium, zinc, vitamins C, B12 and D, and sodium), where the numbers came from, and a recipe's **ingredients**. Tap it again to close.
- **Edit** (pencil icon) a food to fix its values (per 100 g/ml, or per piece/serving with the gram weight). **Additional nutrients** lets you add or correct its micronutrients for the same amount; leave a box blank if you don't know it (blank means unknown, not zero). Foods you edit by hand are never overwritten by later estimates.
- **Delete** (trash icon) a food you no longer want. With a mouse, the icons appear when you hover over a line; on touch screens they're always visible. Past logs keep their numbers.

**Branded foods (Brands):** a packaged product has a pack label, and its numbers should come from that label, not a guess.

1. Name the brand when you log it: `10 g Amul butter`, `1 Britannia Nutrichoice biscuit`. MacBro saves it with its brand. Until you check the label, the numbers are the AI's memory of the label, and the chat card marks the item **check label**.
2. Open **Saved Food → Brands**. Branded foods are grouped by brand (Amul → Butter, Paneer…), and each one shows **label ✓** or **label not checked**. The small number on the **Brands** filter counts the ones still to check.
3. Press **Check label** under a food. OmniAI searches **Open Food Facts**, a free, open database of food labels, for the brand and name, and lists the products it finds with their calories, protein, carbs and fat **per 100 g** (or 100 ml for drinks), the pack size and serving size. Products sold in India come first. Not the right one? Change the words, or type the **barcode number** printed under the pack's barcode for an exact match.
4. Compare with your pack, then press **Use this**. The food now uses the label's numbers (and micronutrients the label lists, like sodium and calcium), plus the serving weight when the label gives one. Nothing changes until you press it.
5. **Also correct the times I've already logged it** (ticked by default) recomputes your past logs of this food with the label's numbers, so your earlier days add up correctly too. Untick it to leave past days as they were.

Not on Open Food Facts, or its numbers don't match your pack? Press the pencil, type the values from the label, and tick **These values are from the pack label** (and, if you like, **Also correct the times I've already logged it**). Either way the food shows **label ✓**, and later AI estimates never overwrite it. Open Food Facts is filled in by volunteers, so always check the numbers against your pack before you use them.

Once a branded food is saved, `10 g amul butter` (brand and name, in either order) is answered straight from Saved Food, without the AI, with the checked label's numbers once you've checked it.

**Recipes** are for dishes you make at home. Make one with **+ Add → Recipe** (above), or in the chat:

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

Each part is its own tile, in this order: day navigation, **macros**, **additional micronutrients** (folded by default), **water**, then **meals** (on a laptop the meals sit beside the other tiles).

| Tile | What you see |
|---|---|
| **Day navigation** | **‹ ›** to move between days (not into the future). |
| **Macros: calorie ring** | Calories **eaten / target**. Beside it: **Balance** (calories left) or **Over budget by**, and **Progress %**. |
| **Macro bars** | Thick bars for Protein (green), Fiber (magenta), Carbs (amber) and Fat (cyan), with current / target above each bar. Bars fill from empty when the tile comes into view. **When you reach a target** the bar turns into a softly moving, glowing gradient. Protein and fiber are goals, so going past them is fine ("goal met ✓"). Carbs and fat are budgets: 100–105% shows "on target ✓", more than that shows how much you're over. |
| **Where today's calories came from** | A split bar of protein, carbs and fat calories (hover for numbers). |
| **Additional micronutrients** | Folded by default, so the day's main goals come first; the heading still says how many are tracked and how many are under half (or over a limit). Tap it to open. It remembers open or closed on this device. Inside: iron, calcium, magnesium, potassium, zinc, vitamin C, vitamin B12 and vitamin D, against daily reference values for your age and sex. Sodium is shown as a limit to stay under. |
| **Water** | Litres against target, quick-add buttons, undo. The bar glows once you reach your goal. |
| **Meals** | Breakfast, Morning snack, Lunch, Evening snack and Dinner, each with its own calories and macros. Tap a meal to expand it and the **pencil** on an item to move, copy, change or delete it. **+ Add food** adds a food to that meal without the chat (see §7). |

Micronutrients are estimates. Treat them as a guide, not a lab result.

## 12. Analysis

The **Analysis** tab shows trends over **7, 14 or 30 days**:

- summary cards: average calories, average protein, average water (your streaks are on **Home**). Analysis's "on target" days still use calories within ±10% and at least 90% of protein; the Home protein streak only looks at protein.
- calories per day and protein per day against target
- macro trends
- where your calories came from
- calories by meal
- water per day
- a data table under each chart

Hover over any chart, or tab to it with the keyboard, to see exact values. A day counts as "on target" when calories are within ±10% of target and protein is at least 90% of target.

## 13. Explore

**Explore** is where ready-made recipe collections will live, each with the macros already worked out. It's **coming soon**: for now the tab previews the planned collections: **High protein**, **Non-veg, quick & easy**, **Healthy desserts**, **Vegetarian protein**, **Under 400 kcal** and **Breakfast ideas**. The tiles can't be opened yet.

## 14. Body Profile

The **Body Profile** tab (it used to be *Settings → Body profile*, then the *Body* tab) shows your body numbers and lets you record measurements. Everything beyond weight and height is optional.

**At the top:**

| Tile | What it shows |
|---|---|
| **Weight** | Your latest weight and the change since the previous one |
| **Height** | Your height, and whether your profile is male or female (used by the diagram and the body-fat formula) |
| **BMI** | Weight (kg) ÷ height (m)², with the WHO adult category: under 18.5 underweight, 18.5–24.9 healthy weight, 25–29.9 overweight, 30 and over obesity. BMI doesn't tell muscle from fat. |
| **Body fat (estimate)** | Worked out with the **US Navy tape-measure equations** (Hodgdon & Beckett, 1984) from your height, **neck** and **waist**, plus **hips** for women. Usually within about ±3–4 percentage points of lab methods. |

**Body fat is only shown when it can be trusted:**

- If a measurement it needs is missing, it says **"Not enough info to estimate"** and names what to add.
- If the numbers can't be right (for example a waist smaller than the neck, or a result outside the human range), it asks you to re-measure instead of showing a number.
- If the measurements it used were taken more than a month apart, it says so.

**Measurements diagram:**

- A front-view figure (male or female, from your profile) with an arrow to each body part: neck, shoulders, chest, biceps, forearm, wrist, waist, hips, thigh and calf.
- **Tap a body part** (on a phone, tap its number or its row in the list) to see **how to measure it**, its latest value and change, and to **add a new value**. Each save is dated, so the history shows how it changes. Values show in cm or inches, following your unit setting.
- For the body-fat estimate, measure as the tips describe: neck just below the Adam's apple, waist at the navel (men) or the narrowest point (women), hips at the widest part.

**Also on this tab:**

- **Update weight & height.** Tick *Recalculate my targets* if you want your calorie and macro targets updated.
- **Measurement history:** each dated entry. **Edit** fixes a mistake in a saved entry (to record a new value, use the diagram so the history keeps the change); **Delete** removes it.

## 15. Settings

Open **⚙ Settings** from the top bar.

| Tab | What you can do |
|---|---|
| **About you** (opens first) | **Basics:** your name, age (from your date of birth), sex, height, country and state (**Change** to pick another from the lists), time zone, goal and activity level. Height and weight are updated on the Body Profile tab. **More about you (optional):** diet, allergies, pace, meal times, training and health; change or clear any of them and press **Save**. If that changes your calculated calories, choose **Use the new target** or **Keep mine**. |
| **Targets** | Edit daily calories, protein, carbs, fat and fiber. |
| **Appearance** | Light, dark, or follow your device (**System**). |
| **Account & privacy** | **Sign-in:** your email, how you sign in (email and password, Google, or both), registration date and last login. **Your data:** when you gave data consent, **Download my data** (a file with everything OmniAI stores about you: profile, logs, foods, chat, usage, and any admin views of your account), and links to **How we use your data** and the **Terms**. |
| **Security** | Change your password (needs the current one). Changing (or setting) your password signs you out on every other device; this one stays logged in. **Log out of all devices** (same tab) signs you out everywhere, including here, e.g. after using a shared computer or losing your phone. If you signed up with Google, it offers **Set password** instead: add one to also log in with your email. **Account & privacy** shows how you sign in. |
| **Delete account** (set apart at the bottom) | Permanently removes your account and **all** your data. Needs your password (or, for Google-only accounts, your email typed out) and can't be undone. |

## 16. Tips for accurate logging

- **Give amounts:** grams, cups, pieces or "a medium bowl". Weighed amounts are the most accurate.
- **Mention oil, butter, ghee and sauces.** They add a lot of calories.
- **Say whether amounts are cooked or raw** for rice, pasta and meat.
- **Name brands** for packaged foods. If MacBro doesn't know a product, it asks you for the label values.
- **Save recipes** for home-cooked dishes you eat often.
- **Correct once, reuse forever:** fix a food in *Saved Food* and every future log uses your numbers.

## 17. Troubleshooting and FAQ

**"You've used all 20 AI messages for today."** Your daily AI allowance is used up (see §5). It resets at midnight. Until then, log foods you've saved, use the water buttons, the Dashboard and quick replies.

**"Too many attempts. Please wait…"** After several wrong passwords for one email (or many sign-in attempts from one connection), sign-in pauses for up to 15 minutes to stop password guessing. Wait and try again.

**"Something went wrong on our side (ref 1a2b3c4d)."** An unexpected error in OmniAI itself. Try again; if it keeps happening, send the **ref** to the contact on the Privacy page so the exact problem can be found.

**"MacBro's servers are temporarily down."** The AI model is unavailable or its free daily limit is used up. Your data is safe. Try again later. You can still use the Dashboard, water buttons and item actions, since they don't need the AI.

**I don't want to use the chat.** Use **+ Add food** under any meal on the Dashboard. Saved foods don't need the AI at all; new foods need it once, for the estimate.

**The mic button is missing.** Your browser doesn't support speech recognition. Use Chrome or Edge, or type instead.

**I confirmed the wrong thing.** Fix it on the Dashboard with the **pencil** on that item, or ask in the chat, e.g. "delete the pizza from lunch".

**The meal was put in the wrong slot.** Move it with **pencil → Move → pick the meal → →**, or say "move it to lunch".

**Why do some replies arrive instantly?** Common messages, like a water amount, "yes", "what's left today?", foods you've saved in Saved Food ("had 3 eggs for breakfast"), common foods on the general food list ("150 g banana"), the raw/cooked question or "same breakfast as yesterday", are handled by the app directly without the AI. They're instant, and they save the free AI quota for harder messages.

**I typed "yes" but nothing was saved.** Tap **Looks good** on the card. Typing isn't enough, so that you always see what's being saved.

**Why didn't MacBro say "logged"?** MacBro never saves anything on its own. Only your button press saves.

**Can other users see my data?** No. Administrators can view account data read-only for support and development, as described in the consent notice, and every admin view is recorded in an audit log.
