/**
 * Explore tab: a home for ready-made recipe collections. For now it only previews the planned
 * collections; nothing here is clickable yet (see docs/open-points.md, "Explore recipes").
 */
const COLLECTIONS = [
  { key: "high-protein", title: "High protein", blurb: "Meals that make your protein target easy.", tone: "protein" },
  { key: "non-veg-quick", title: "Non-veg, quick & easy", blurb: "Chicken, eggs and fish in 20 minutes or less.", tone: "carbs" },
  { key: "healthy-desserts", title: "Healthy desserts", blurb: "Sweet treats that fit your macros.", tone: "fiber" },
  { key: "veg-protein", title: "Vegetarian protein", blurb: "Paneer, dal, tofu and more.", tone: "protein" },
  { key: "light-meals", title: "Under 400 kcal", blurb: "Filling meals for a lighter day.", tone: "fat" },
  { key: "breakfast", title: "Breakfast ideas", blurb: "Start the day with a good mix of macros.", tone: "carbs" },
] as const;

export default function ExplorePage() {
  return (
    <section className="explore card" aria-labelledby="explore-heading">
      <h2 id="explore-heading">Explore</h2>
      <p className="muted small">
        Recipe collections with the macros already worked out, ready to log in one tap. They're on the way;
        here's what's planned.
      </p>
      <ul className="explore-grid">
        {COLLECTIONS.map((c) => (
          <li key={c.key} className={`explore-tile ${c.tone}`}>
            <span className="explore-accent" aria-hidden="true" />
            <div className="explore-title">{c.title}</div>
            <p className="muted small">{c.blurb}</p>
            <span className="badge">Coming soon</span>
          </li>
        ))}
      </ul>
    </section>
  );
}
