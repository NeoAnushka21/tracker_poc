import { useEffect, useState } from "react";
import { api } from "../api";
import type { DailySummary, Entry } from "../types";
import { MEAL_LABEL, friendlyDate, grams, kcal, shiftDay, time } from "../format";

const MEAL_ORDER = ["breakfast", "lunch", "snack", "dinner"];

function Bar({ label, value, target, unit }: { label: string; value: number; target: number; unit: string }) {
  const pct = target > 0 ? Math.min(100, (value / target) * 100) : 0;
  const over = target > 0 && value > target;
  const fmt = (n: number) => (unit === "kcal" ? Math.round(n).toLocaleString() : `${Math.round(n)}`);
  return (
    <div className="bar-row">
      <div className="bar-label">
        <span>{label}</span>
        <span className="num">
          {fmt(value)} / {fmt(target)} {unit}
        </span>
      </div>
      <div className="bar" role="progressbar" aria-valuenow={Math.round(value)} aria-valuemax={target} aria-label={label}>
        <div className={`bar-fill ${over ? "over" : ""}`} style={{ width: `${pct}%` }} />
      </div>
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
  const remaining = data.remaining?.calories ?? 0;
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
          <div className="kcal-hero">
            <div>
              <div className="big num">{Math.round(c.calories).toLocaleString()}</div>
              <div className="muted small">eaten</div>
            </div>
            <div className={remaining < 0 ? "warn" : ""}>
              <div className="big num">{Math.abs(Math.round(remaining)).toLocaleString()}</div>
              <div className="muted small">{remaining < 0 ? "over budget" : "remaining"}</div>
            </div>
          </div>
          <Bar label="Calories" value={c.calories} target={t.calories} unit="kcal" />
          <Bar label="Protein" value={c.protein_g} target={t.protein_g} unit="g" />
          <Bar label="Carbs" value={c.carbs_g} target={t.carbs_g} unit="g" />
          <Bar label="Fat" value={c.fat_g} target={t.fat_g} unit="g" />
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
