import { useEffect, useRef, useState } from "react";
import { ArrowRightIcon, BowlIcon, DumbbellIcon } from "./icons";

/**
 * Explore tab: two sections, Recipes and Workouts. The landing view shows one card per section;
 * opening one lists what's planned there. Nothing inside is clickable yet (see
 * docs/open-points.md, "Explore recipes" and "Explore workouts").
 */
type Tile = { key: string; title: string; blurb: string; tone: "protein" | "carbs" | "fat" | "fiber" };

const RECIPES: Tile[] = [
  { key: "high-protein", title: "High protein", blurb: "Meals that make your protein target easy.", tone: "protein" },
  { key: "non-veg-quick", title: "Non-veg, quick & easy", blurb: "Chicken, eggs and fish in 20 minutes or less.", tone: "carbs" },
  { key: "healthy-desserts", title: "Healthy desserts", blurb: "Sweet treats that fit your macros.", tone: "fiber" },
  { key: "veg-protein", title: "Vegetarian protein", blurb: "Paneer, dal, tofu and more.", tone: "protein" },
  { key: "light-meals", title: "Under 400 kcal", blurb: "Filling meals for a lighter day.", tone: "fat" },
  { key: "breakfast", title: "Breakfast ideas", blurb: "Start the day with a good mix of macros.", tone: "carbs" },
];

const WORKOUTS: Tile[] = [
  { key: "strength-basics", title: "Strength training basics", blurb: "Form, sets, reps and how to progress safely.", tone: "protein" },
  { key: "beginner-full-body", title: "Beginner full-body routine", blurb: "Three days a week, the main lifts.", tone: "fat" },
  { key: "home-workouts", title: "Home workouts", blurb: "No equipment, 20 to 30 minutes.", tone: "carbs" },
  { key: "warm-up", title: "Warm-up and mobility", blurb: "Short routines before and after training.", tone: "fiber" },
  { key: "cardio", title: "Cardio and daily steps", blurb: "Easy ways to move more through the day.", tone: "fat" },
  { key: "recovery", title: "Recovery and rest", blurb: "Sleep, rest days and eating around training.", tone: "protein" },
];

const SECTIONS = {
  recipes: {
    title: "Recipes", Icon: BowlIcon, items: RECIPES, unit: "collections",
    blurb: "Recipe collections with the macros already worked out, ready to log in one tap.",
  },
  workouts: {
    title: "Workouts", Icon: DumbbellIcon, items: WORKOUTS, unit: "topics",
    blurb: "Workout basics, tips and simple routines to go with your nutrition.",
  },
} as const;
type SectionId = keyof typeof SECTIONS;

function Tiles({ items }: { items: Tile[] }) {
  return (
    <ul className="explore-grid">
      {items.map((c) => (
        <li key={c.key} className={`explore-tile ${c.tone}`}>
          <span className="explore-accent" aria-hidden="true" />
          <div className="explore-title">{c.title}</div>
          <p className="muted small">{c.blurb}</p>
          <span className="badge">Coming soon</span>
        </li>
      ))}
    </ul>
  );
}

export default function ExplorePage() {
  const [open, setOpen] = useState<SectionId | null>(null);
  const heading = useRef<HTMLHeadingElement>(null);
  const opened = useRef(false);
  // Moving between the landing view and a section: put keyboard focus on the new heading.
  useEffect(() => {
    if (opened.current) heading.current?.focus();
    opened.current = true;
  }, [open]);

  if (open) {
    const s = SECTIONS[open];
    return (
      <section className="explore card" aria-labelledby="explore-heading">
        <button type="button" className="link explore-back" onClick={() => setOpen(null)}>‹ Explore</button>
        <div className={`explore-section-head ${open}`}>
          <span className="explore-icon" aria-hidden="true"><s.Icon /></span>
          <div>
            <h2 id="explore-heading" ref={heading} tabIndex={-1}>{s.title}</h2>
            <p className="muted small">{s.blurb} They're on the way; here's what's planned.</p>
          </div>
        </div>
        <Tiles items={s.items} />
      </section>
    );
  }

  return (
    <section className="explore card" aria-labelledby="explore-heading">
      <h2 id="explore-heading" ref={heading} tabIndex={-1}>Explore</h2>
      <p className="muted small">Ideas for what to eat and how to train. Pick a section.</p>
      <div className="explore-sections">
        {(Object.keys(SECTIONS) as SectionId[]).map((id) => {
          const s = SECTIONS[id];
          return (
            <button key={id} type="button" className={`explore-section ${id}`} onClick={() => setOpen(id)}>
              <span className="explore-icon" aria-hidden="true"><s.Icon /></span>
              <span className="explore-section-text">
                <b>{s.title}</b>
                <span className="muted small">{s.blurb}</span>
                <span className="explore-count">{s.items.length} {s.unit} planned</span>
              </span>
              <span className="explore-go" aria-hidden="true"><ArrowRightIcon /></span>
            </button>
          );
        })}
      </div>
    </section>
  );
}
