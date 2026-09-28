import { useEffect, useState } from "react";
import { api } from "../api";
import type { DailySummary, Entry, Item, MicroSummary, WaterSummary } from "../types";
import { MEAL_LABEL, MEAL_ORDER, friendlyDate, grams, kcal, litres, shiftDay } from "../format";

/** A meter: one macro against its target. Identity comes from the label; the fill hue repeats it. */
function Bar({ label, value, target, unit, tone }: {
  label: string; value: number; target: number; unit: string; tone: "protein" | "fiber" | "carbs" | "fat";
}) {
  const pct = target > 0 ? Math.min(100, (value / target) * 100) : 0;
  const left = Math.round(target - value);
  // Going past the fiber target is fine, so it never shows as a warning.
  const over = target > 0 && value > target && tone !== "fiber";
  const met = tone === "fiber" && target > 0 && value >= target;
  return (
    <div className={`bar-row ${tone}`} title={`${label}: ${Math.round(value)} of ${target} ${unit}`}>
      <div className="bar-label">
        <span className="bar-name"><i className="swatch" aria-hidden="true" />{label}</span>
        <span className="num">
          {Math.round(value)} / {target} {unit}
          <span className={over ? "warn" : "muted"}>
            {" · "}{met ? "goal met ✓" : over ? `${-left} ${unit} over` : `${left} ${unit} left`}
          </span>
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

function fmtMicro(v: number): string {
  return v >= 100 ? Math.round(v).toLocaleString() : String(Math.round(v * 10) / 10);
}

/** Secondary panel: one muted hue for every nutrient; the label carries identity. */
function Micronutrients({ m }: { m: MicroSummary }) {
  return (
    <section className="micros" aria-labelledby="micros-heading">
      <h3 id="micros-heading">Additional micronutrients</h3>
      <p className="muted small">
        Approximate: estimated by the assistant from typical food data.
        {m.items_total > 0 && m.items_with_data < m.items_total &&
          ` ${m.items_with_data} of ${m.items_total} items today have estimates (older entries don't).`}
      </p>
      <div className="micro-grid">
        {m.nutrients.map((n) => {
          const pct = n.target > 0 ? Math.min(100, (n.consumed / n.target) * 100) : 0;
          const over = n.kind === "limit" && n.consumed > n.target;
          return (
            <div key={n.key} className={`micro ${n.kind}`} title={`${n.label}: ${fmtMicro(n.consumed)} of ${n.target} ${n.unit}`}>
              <div className="micro-label">
                <span>{n.label}{n.kind === "limit" && <span className="muted"> (limit)</span>}</span>
                <span className={`num ${over ? "warn" : ""}`}>
                  {fmtMicro(n.consumed)} / {n.target.toLocaleString()} {n.unit}
                </span>
              </div>
              <div className="bar" role="progressbar" aria-label={n.label}
                   aria-valuenow={Math.round(n.consumed)} aria-valuemax={n.target}>
                <div className={`bar-fill ${over ? "over" : ""}`} style={{ width: `${pct}%` }} />
              </div>
            </div>
          );
        })}
      </div>
    </section>
  );
}

function WaterDrop() {
  return (
    <svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true">
      <path d="M12 3c3.5 4.4 6 7.9 6 11a6 6 0 0 1-12 0c0-3.1 2.5-6.6 6-11z" fill="currentColor" />
    </svg>
  );
}

/** Independent water tracker: quick-add buttons save directly (they're the user's own clicks). */
function Water({ w, isToday, onChanged }: { w: WaterSummary; isToday: boolean; onChanged: () => void }) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const target = w.target_ml ?? 0;
  const pct = target > 0 ? Math.min(100, (w.consumed_ml / target) * 100) : 0;
  const met = target > 0 && w.consumed_ml >= target;
  const last = w.logs[w.logs.length - 1];

  async function run(fn: () => Promise<unknown>) {
    setBusy(true);
    setError(null);
    try {
      await fn();
      onChanged();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="water" aria-labelledby="water-heading">
      <div className="water-head">
        <h3 id="water-heading"><span className="water-icon"><WaterDrop /></span>Water</h3>
        <span className="num">
          {litres(w.consumed_ml)}{target > 0 && ` / ${litres(target)}`}
          <span className="muted">
            {target > 0 && (met ? " · goal met ✓" : ` · ${litres(target - w.consumed_ml)} to go`)}
          </span>
        </span>
      </div>
      <div className="bar water-bar" role="progressbar" aria-label="Water"
           aria-valuenow={w.consumed_ml} aria-valuemax={target}>
        <div className="bar-fill" style={{ width: `${pct}%` }} />
      </div>
      {isToday && (
        <div className="water-actions">
          <button onClick={() => run(() => api.addWater(250))} disabled={busy}>+ 250 ml</button>
          <button onClick={() => run(() => api.addWater(500))} disabled={busy}>+ 500 ml</button>
          <button className="ghost" onClick={() => last && run(() => api.deleteWater(last.id))}
                  disabled={busy || !last} title={last ? `Remove the last ${last.amount_ml} ml` : undefined}>
            Undo
          </button>
          <span className="muted small">or tell the chat, e.g. "drank 1 L water"</span>
        </div>
      )}
      {!target && <p className="muted small">Add your weight under Targets &amp; weight to get a daily water goal.</p>}
      {error && <p className="error small">{error}</p>}
    </section>
  );
}

function sumItems(items: Item[]) {
  return items.reduce(
    (t, i) => ({
      calories: t.calories + i.calories, protein_g: t.protein_g + i.protein_g, fiber_g: t.fiber_g + (i.fiber_g ?? 0),
      carbs_g: t.carbs_g + i.carbs_g, fat_g: t.fat_g + i.fat_g,
    }),
    { calories: 0, protein_g: 0, fiber_g: 0, carbs_g: 0, fat_g: 0 },
  );
}

/** One meal: its own macro breakdown, then each food on its own line. */
function MealSection({ meal, entries }: { meal: string; entries: Entry[] }) {
  const items = entries.flatMap((e) => e.items);
  const t = sumItems(items);
  return (
    <div className={`meal-card ${items.length ? "" : "empty"}`}>
      <div className="meal-head">
        <span className="meal-name">{MEAL_LABEL[meal] ?? meal}</span>
        <span className="num">{items.length ? kcal(t.calories) : "–"}</span>
      </div>
      {items.length > 0 ? (
        <>
          <div className="meal-macros">
            <span className="macro-chip protein"><i />P {grams(t.protein_g)}</span>
            <span className="macro-chip fiber"><i />Fiber {grams(t.fiber_g)}</span>
            <span className="macro-chip carbs"><i />C {grams(t.carbs_g)}</span>
            <span className="macro-chip fat"><i />F {grams(t.fat_g)}</span>
          </div>
          <ul className="meal-items">
            {items.map((it, idx) => (
              <li key={idx}>
                <span className="meal-item-name">
                  {it.ingredient_name}
                  {it.brand_name && <span className="muted"> · {it.brand_name}</span>}
                </span>
                <span className="muted meal-item-qty">{it.quantity} {it.unit}</span>
                <span className="num">{Math.round(it.calories)}</span>
              </li>
            ))}
          </ul>
        </>
      ) : (
        <p className="muted small">Nothing logged</p>
      )}
    </div>
  );
}

type DashboardProps = { dataVersion: number; onDataChanged: () => void };

export default function Dashboard({ dataVersion, onDataChanged }: DashboardProps) {
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
          <Bar label="Fiber" value={c.fiber_g} target={t.fiber_g} unit="g" tone="fiber" />
          <Bar label="Carbs" value={c.carbs_g} target={t.carbs_g} unit="g" tone="carbs" />
          <Bar label="Fat" value={c.fat_g} target={t.fat_g} unit="g" tone="fat" />
        </>
      ) : (
        <p className="muted">No targets set.</p>
      )}

      {data.water && <Water w={data.water} isToday={data.date === today} onChanged={onDataChanged} />}

      {data.micronutrients && <Micronutrients m={data.micronutrients} />}

      <h3>Meals</h3>
      <div className="meals">
        {[...MEAL_ORDER, ...Object.keys(byMeal).filter((m) => !MEAL_ORDER.includes(m))].map((meal) => (
          <MealSection key={meal} meal={meal} entries={byMeal[meal] ?? []} />
        ))}
      </div>
    </section>
  );
}
