import { useEffect, useState } from "react";
import { api } from "../api";
import type { DailySummary, Entry } from "../types";
import { MEAL_LABEL, friendlyDate, grams, kcal, shiftDay, time } from "../format";

const MEAL_ORDER = ["breakfast", "lunch", "snack", "dinner"];

/** A meter: one macro against its target. Identity comes from the label; the fill hue repeats it. */
function Bar({ label, value, target, unit, tone }: {
  label: string; value: number; target: number; unit: string; tone: "protein" | "carbs" | "fat";
}) {
  const pct = target > 0 ? Math.min(100, (value / target) * 100) : 0;
  const over = target > 0 && value > target;
  const left = Math.round(target - value);
  return (
    <div className={`bar-row ${tone}`} title={`${label}: ${Math.round(value)} of ${target} ${unit}`}>
      <div className="bar-label">
        <span className="bar-name"><i className="swatch" aria-hidden="true" />{label}</span>
        <span className="num">
          {Math.round(value)} / {target} {unit}
          <span className={over ? "warn" : "muted"}> · {over ? `${-left} ${unit} over` : `${left} ${unit} left`}</span>
        </span>
      </div>
      <div className="bar" role="progressbar" aria-valuenow={Math.round(value)} aria-valuemax={target} aria-label={label}>
        <div className={`bar-fill ${over ? "over" : ""}`} style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
}

/** Calorie meter as a ring: remaining kcal is the headline, eaten/target beside it. */
function CalorieRing({ eaten, target }: { eaten: number; target: number }) {
  const r = 52;
  const circumference = 2 * Math.PI * r;
  const frac = target > 0 ? Math.min(1, eaten / target) : 0;
  const remaining = Math.round(target - eaten);
  const over = remaining < 0;
  return (
    <div className="kcal-ring-wrap">
      <svg className={`kcal-ring ${over ? "over" : ""}`} viewBox="0 0 120 120" role="img"
           aria-label={`${Math.round(eaten)} of ${target} kcal eaten`}>
        <title>{`${Math.round(eaten)} of ${target} kcal eaten`}</title>
        <circle className="ring-track" cx="60" cy="60" r={r} />
        <circle className="ring-fill" cx="60" cy="60" r={r}
                strokeDasharray={`${frac * circumference} ${circumference}`}
                transform="rotate(-90 60 60)" />
        <text x="60" y="58" className="ring-value">{Math.abs(remaining).toLocaleString()}</text>
        <text x="60" y="76" className="ring-caption">{over ? "kcal over" : "kcal left"}</text>
      </svg>
      <dl className="kcal-stats">
        <div><dt>Eaten</dt><dd>{Math.round(eaten).toLocaleString()}</dd></div>
        <div><dt>Budget</dt><dd>{target.toLocaleString()}</dd></div>
        <div><dt>Progress</dt><dd>{target > 0 ? Math.round((eaten / target) * 100) : 0}%</dd></div>
      </dl>
    </div>
  );
}

export default function Dashboard({ dataVersion }: { dataVersion: number }) {
  const [day, setDay] = useState<string | undefined>(undefined);
  const [today, setToday] = useState<string | null>(null);
  const [data, setData] = useState<DailySummary | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.daily(day)
      .then((d) => {
        setData(d);
        if (!day) setToday(d.date);
        setError(null);
      })
      .catch((e) => setError(e.message));
  }, [day, dataVersion]);

  if (error) return <section className="dashboard card error">{error}</section>;
  if (!data || !today) return <section className="dashboard card muted">Loading…</section>;

  const t = data.targets;
  const c = data.consumed;
  const byMeal: Record<string, Entry[]> = {};
  for (const e of data.entries) (byMeal[e.meal_type] ??= []).push(e);

  return (
    <section className="dashboard card">
      <div className="day-nav">
        <button className="ghost" onClick={() => setDay(shiftDay(data.date, -1))} aria-label="Previous day">‹</button>
        <span className="day-label">{friendlyDate(data.date, today)}</span>
        <button className="ghost" onClick={() => setDay(shiftDay(data.date, 1))} disabled={data.date >= today} aria-label="Next day">›</button>
      </div>

      {t ? (
        <>
          <CalorieRing eaten={c.calories} target={t.calories} />
          <Bar label="Protein" value={c.protein_g} target={t.protein_g} unit="g" tone="protein" />
          <Bar label="Carbs" value={c.carbs_g} target={t.carbs_g} unit="g" tone="carbs" />
          <Bar label="Fat" value={c.fat_g} target={t.fat_g} unit="g" tone="fat" />
          <div className="muted small">Fiber: {grams(c.fiber_g)}</div>
        </>
      ) : (
        <p className="muted">No targets set.</p>
      )}

      <h3>Meals</h3>
      {data.entries.length === 0 && <p className="muted small">Nothing logged{data.date === today ? " yet today" : ""}.</p>}
      {MEAL_ORDER.filter((m) => byMeal[m]).map((meal) => (
        <div key={meal} className="meal-group">
          <div className="meal-head">
            <span>{MEAL_LABEL[meal]}</span>
            <span className="muted num">{kcal(byMeal[meal].reduce((s, e) => s + e.totals.calories, 0))}</span>
          </div>
          {byMeal[meal].map((e) => (
            <div key={e.id} className="entry">
              <span className="muted num">{time(e.eaten_at)}</span>
              <span className="entry-items">
                {e.items.map((i) => `${i.quantity} ${i.unit} ${i.ingredient_name}`).join(", ")}
              </span>
              <span className="num">{Math.round(e.totals.calories)}</span>
            </div>
          ))}
        </div>
      ))}
    </section>
  );
}
