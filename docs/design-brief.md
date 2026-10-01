# OmniAI: frontend design brief

> **Note (2026-10-01):** the app has since been renamed **Tandurust**, with a new logo (see `frontend/src/brand.ts`, `docs/brand/`); its address is now https://tandurust-app.onrender.com. The brief below is kept as written on 2026-09-29.

> Prepared 2026-09-29 for the design team. It describes the app as it is today, the parts that are fixed, and where design can help most. Screenshots are in [`design-brief/`](design-brief/) and use a demo account with sample data. Updated the same day after the reward-style UI pass (section 3: tokens, shape and motion); screenshots taken before it show the older palette.

## 1. The product in one minute

**OmniAI** (working name) is a calorie and macro tracker you use by **chatting**. You type or say what you ate ("2 eggs and a slice of toast for breakfast"). The assistant, **MacBro**, works out the nutrition and shows it as a card. **Nothing is saved until you press "Looks good"**, so the user stays in control. Foods you confirm are remembered, so repeat meals get exactly the same numbers.

- **Users:** adults tracking food for weight goals or general health, mostly in India for now (metric by default, Indian foods common). Right now one person uses it daily; small groups of testers come later.
- **Platforms:** a web app that works on phones and laptops, with one codebase. A phone app is planned for later, starting as an installable web app.
- **Try it:** https://tandurust-app.onrender.com (was omniai-app). The free server sleeps when idle, so the first visit can take up to a minute; a dancing-MacBro screen shows meanwhile.

**Naming rules:**
- The **app** is *OmniAI*, with a placeholder logo: the letters **"OAI"** on a green tile. Both the name and the logo are temporary.
- The **assistant** is *MacBro*, a friendly cartoon character (a boy in an "MB" t-shirt).
- MacBro appears **only in Chat** and on the **loading screen**. Everywhere else uses the app name and logo.

## 2. Screens

The app has a top bar (logo, **? Guide**, **⚙ Settings**, **Log out**, user initials; since 2026-09-29 the top bar and tabs share a frosted-glass header over a soft green / cyan / violet / pink / amber mesh) and **seven tabs** in the same order on phone and laptop:

**Home · Chat · Dashboard · Analysis · Saved Food · Explore · Body Profile**

| Screen | Purpose | Key parts | Screenshots |
|---|---|---|---|
| **Login / Create account** | Get in | Email + password, or **Continue with Google** (being added). Consent checkbox on sign-up, "For adults 18 and over · Privacy" link, **Forgot password?**, light/dark switch in the corner. Separate **Admin login** mode. | – |
| **Before we continue** | Re-consent when the privacy wording changes | Consent text, **Agree and continue**, **Log out instead** | – |
| **Onboarding** | First-time profile | Name, date of birth, sex, height, weight, units, time zone, goal, activity level, then an editable preview of daily targets | – |
| **First-run tour** | Explain the app once | A panel docked at the bottom that switches tabs step by step (9 steps); reopened from **? Guide** | – |
| **Home** (default) | Today at a glance | Greeting ("Good evening, Sam!") with **Log a meal**; *Today's summary* (calorie ring, Balance, Progress %, protein / fiber / carbs / fat bars); separate **Water** tile (+250 ml, +500 ml, Undo); two **streak** cards (meal logging, and protein: days with at least 85% of the protein target) with the last 7 days as ticks | `home-light-1280.png`, `home-light-390.png`, `home-dark-1280.png` |
| **Chat** | Log and ask by talking to MacBro | One chat per day, with **Show earlier chat**. Message bubbles; **proposal cards** (items with kcal and macro chips, *Not saved yet*, **Looks good / Needs changes / Cancel**); a **Day so far** card after food and a **Water today** card after water; **Logging for** date picker; pill-shaped input with mic and Send; **■ Stop** while MacBro thinks; example chips when empty | `chat-light-1280.png`, `chat-light-390.png`, `chat-dark-1280.png` |
| **Dashboard** | One day in detail | Day switcher (‹ Today ›), then separate tiles: **macros** (ring, bars, "Where today's calories came from" split bar), **micronutrients** (9 small bars), **water**, and **meals** (Breakfast, Morning snack, Lunch, Evening snack, Dinner). Each food has a pencil that opens an edit panel (move/copy to another meal, change amount, delete, edit in chat). **+ Add food** per meal (being added): pick a saved food or type any food; new foods get an AI estimate to check first. | `dashboard-light-1280.png`, `dashboard-light-390.png`, `dashboard-dark-1280.png` |
| **Analysis** | Trends | 7 / 14 / 30-day switch; stat cards (avg calories, protein, water); charts: calories per day, protein per day, macro trends, water per day, where calories came from, calories by meal; hover tooltips; **Show data table** | `analysis-light-1280.png`, `analysis-light-390.png` |
| **Saved Food** | The personal food library | Search, All / Foods / Recipes filter; one card per food (kcal in bold, P / C / F / Fiber chips, source line, folded **Micronutrients**); pencil to edit (all numbers, plus *Additional nutrients*), trash to delete; recipes show ingredients | `foods-light-1280.png`, `foods-light-390.png` |
| **Explore** | Recipe collections (planned) | Coming-soon tiles: High protein, Non-veg quick & easy, Healthy desserts, Vegetarian protein, Under 400 kcal, Breakfast ideas | – |
| **Body Profile** | Body numbers and measurements | Tiles: weight, height, **BMI** with a category chip, **Body fat (estimate)** (or "Not enough info…"). A **front-view male/female figure** with arrows to 10 body parts (tap to see how to measure and add a value); on phones, numbered dots and a list. Weight/height update and measurement history. | `body-light-1280.png`, `body-light-390.png`, `body-dark-1280.png` |
| **Settings** (dialog) | Account and preferences | Account (details, appearance: light / dark / system, **Download my data**, being added), Targets, Password, Delete account | – |
| **Privacy** page | Plain-language privacy notice | Being added | – |
| **Admin console** | For the app's administrators only | Users table, per-user detail (read-only), audit log, AI usage | – |
| **Loading / wake screen** | While the free server wakes (up to ~1 minute) | MacBro bouncing and swaying with floating music notes, rotating lines ("MacBro is warming up the kitchen…"), pulsing dots; **Try again** after 3 minutes; still version for "reduce motion" | – |

"Being added" means it's built but not yet live.

## 3. Visual language today

**Font:** Plus Jakarta Sans (variable, self-hosted). Headings: h1 1.6rem/700, h2 1.25rem/700, h3 1rem/650. Numbers use tabular figures.

**Shape and depth:** white cards on an off-white background, 22px corner radius (14px for smaller elements), wide, faint shadows, pill-shaped buttons and tabs, and a sliding gradient underline under the active tab.

**Colour tokens.** Every colour is a named token with a light and a dark value; the palette is a single CSS file, so a new palette is quick to apply.

| Token | Light | Dark | Used for |
|---|---|---|---|
| Background | `#fafafa` | `#121212` | Page |
| Surface / surface 2 | `#ffffff` / `#f4f4f5` | `#1c1c1f` / `#26262a` | Cards / insets |
| Text / muted | `#18181b` / `#5c5c66` | `#ececef` / `#a1a1aa` | Body text / secondary text |
| Border | `#e7e7ea` | `#2e2e33` | Card and input borders |
| Accent | `#047857` | `#34d399` | Primary buttons, links, active tab |
| Accent gradient | `#047857 → #0e7490` | `#34d399 → #22d3ee` | Primary buttons, logo tile, underline |
| **Protein** | `#10b476` | `#15ad52` | Macro bars, chips, legends |
| **Fiber** | `#c73e91` | `#c94696` | 〃 |
| **Carbs** | `#e68a0a` | `#d17f08` | 〃 |
| **Fat** | `#0b9ad0` | `#089fbf` | 〃 |
| **Water** | `#4a3aa7` | `#8a7fe6` | Water bar and cards |
| Warning / error | `#b45309` / `#b42318` | `#f0a24a` / `#f47067` | Over budget, errors |

The four macro colours and water were **checked for colour-blind separation and contrast** with a palette validator. If they change, they should be re-checked, and every coloured mark keeps a text label, so colour is never the only cue.

**Charts:** hand-drawn SVG (no chart library): rounded bar tops, dashed grid lines, no axis lines, a dark tooltip with an arrow, and a data table under each chart.

**Icons:** a mix today. There are thin line icons (pencil, trash, close, check, arrow, chat, water drop), emoji and symbols in places (⚙, ?, 📅, ♪, ▲▼), and the MacBro illustration.

**Motion** (reward pass, 2026-09-29): new chat cards spring in (95% → 100% with a small overshoot); rings and bars fill with an ease-out when they come into view; a bar that reaches its target turns into a slow-moving gradient with a glow; buttons press to 98%; MacBro nods with floating maths symbols while thinking; a streak completed today pops once. Also the sliding tab underline, card hover lift and the wake-screen dance. On Android phones, small vibrations mark a save, a water tap and a completed streak. Everything respects "reduce motion".

## 4. Responsive behaviour

- **Phone (under 860px):** one column; the tabs scroll sideways; grids collapse to 1–2 columns.
- **Laptop (1024px and up):** content is capped at **1200px** and lines up with the top bar. Pages use extra columns rather than stretching:
  - **Home:** summary left; water and streaks right.
  - **Dashboard:** macro, micronutrient and water tiles left; meals right.
  - **Analysis:** charts in pairs.
  - **Saved Food:** cards in two columns.
  - **Body:** figure with labelled arrows and the editor beside it.
- **Chat:** message bubbles are capped at 780px so lines stay readable.

## 5. Fixed constraints (please design within these)

| Constraint | Why |
|---|---|
| **Nothing is saved until the user confirms** a card (Looks good / Needs changes / Cancel) | The core trust rule: AI estimates are always checked |
| **Same top tabs on phone and laptop** | Owner decision (a left sidebar on laptops was considered and declined) |
| **MacBro only in Chat and the loading screen** | Keeps the app brand separate from the assistant character |
| **Light and dark mode** for everything | Both are used; dark is its own palette, not an automatic inversion |
| **Accessibility:** WCAG AA contrast, keyboard access, visible focus, labels on every coloured mark, "reduce motion" | Already met today; keep it |
| **Estimates are labelled as estimates** (micronutrients, body fat ±3–4 points, BMI "a rough guide") | Health numbers must not look more exact than they are |
| **Tech:** React, one CSS file of tokens, no UI component library, SVG for charts and the body figure; the Plus Jakarta Sans font is self-hosted, not loaded from Google | Keep the app light and free of paid or closed assets. Designs made from tokens (colour, radius, spacing, type scale) are the easiest to apply. |
| **Free and open source** | Fonts, icons and illustrations need open licences (e.g. OFL fonts, MIT/ISC or CC0 icons) |

## 6. Where design can help most

1. **Brand identity:** a real name (if it changes), a logo to replace the "OAI" tile, a favicon and app icon, and possibly a refreshed MacBro character.
2. **One icon set:** replace the mix of emoji and line icons with one consistent open-licence set.
3. **Type and spacing scale:** sizes and spacing grew screen by screen; a defined scale would tidy every page.
4. **Chat cards:** the proposal card (items, numbers, three buttons) and the summary cards are the heart of the app; they could be clearer and more compact, especially on phones.
5. **Dashboard on phones:** a full day is a long scroll (macros, micronutrients, water, 5 meals); ideas for summarising or collapsing are welcome.
6. **Empty and first-use states:** a new user sees empty charts, "Nothing logged" meals and "–" tiles; these could guide the first log instead.
7. **Body figure:** a simple flat outline with arrows (the chest and biceps arrows cross the arm). A more polished, inclusive illustration style would help; it must still work in light and dark mode and at phone size.
8. **Onboarding and forms:** the onboarding and settings forms are plain and functional.
9. **Loading moments:** the dancing-MacBro wake screen, and a matching "MacBro is thinking" state in Chat (planned).
10. **Future phone app:** home-screen icon, splash screen and reminder notifications (see `open-points.md` §7).

## 7. What would help us most from design

- A **token sheet** (colours for light and dark, type scale, spacing, radius, shadow), so it maps one-to-one onto the CSS file.
- **Screen designs** for Home, Chat (including cards), Dashboard and Body, at phone and laptop sizes, in both themes.
- **Component specs** for buttons, tabs, cards, chips, bars, inputs and dialogs, with hover, focus, disabled, loading and error states.
- Assets in **SVG**, with licences noted.

## 8. More detail

- What users see and do, step by step: [user-guide.md](user-guide.md)
- Architecture and components: [technical-overview.md](technical-overview.md) §7
- Ideas already discussed and parked: [open-points.md](open-points.md)
