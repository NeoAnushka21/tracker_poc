import { useEffect, useState } from "react";
import { api } from "../api";
import type { RangeDay, RangeSummary } from "../types";
import { MEAL_LABEL, MEAL_ORDER, litres } from "../format";
import { BarChart, DataTable, LineChart, StackedBar, StatTile, type Point } from "./charts";

const RANGES = [7, 14, 30] as const;

function dayLabels(days: RangeDay[]) {
  const short = days.length <= 7;
  return days.map((d) => {
    const dt = new Date(`${d.date}T12:00:00`);
    return {
      label: short ? dt.toLocaleDateString(undefined, { weekday: "short" }) : String(dt.getDate()),
      title: dt.toLocaleDateString(undefined, { weekday: "short", day: "numeric", month: "short" }),
    };
  });
}

const n = (v: number | null | undefined, digits = 0) => (v == null ? "–" : v.toFixed(digits));

export default function AnalysisPage({ dataVersion }: { dataVersion: number }) {
  const [days, setDays] = useState<(typeof RANGES)[number]>(7);
  const [data, setData] = useState<RangeSummary | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.range(days).then((d) => { setData(d); setError(null); }).catch((e) => setError(e.message));
  }, [days, dataVersion]);

  const header = (
    <div className="analysis-head">
      <div>
        <h2>Advanced analysis</h2>
        <p className="muted small">Trends from your confirmed logs. Hover or tap a day for details.</p>
      </div>
      <div className="segmented" role="radiogroup" aria-label="Range">
        {RANGES.map((r) => (
          <button key={r} type="button" role="radio" aria-checked={days === r} className={days === r ? "on" : ""} onClick={() => setDays(r)}>
            {r} days
          </button>
        ))}
      </div>
    </div>
  );

  if (error) return <section className="analysis card">{header}<p className="error">{error}</p></section>;
  if (!data) return <section className="analysis card">{header}<p className="muted">Loading…</p></section>;

  const s = data.summary;
  const labels = dayLabels(data.days);
  const latest = [...data.days].reverse().find((d) => d.targets)?.targets ?? null;
  const pts = (key: "calories" | "protein_g", target: (d: RangeDay) => number | null): Point[] =>
    data.days.map((d, i) => ({ ...labels[i], value: d.logged ? d[key] : null, target: target(d) }));
  const rule = s.adherence_rule;

  if (s.days_logged === 0) {
    return (
      <section className="analysis card">
        {header}
        <div className="empty-analysis">
          <p><b>No confirmed logs in the last {days} days yet.</b></p>
          <p className="muted">Log a few meals in the chat and your trends will show up here. Daily stats appear
            after the first day, and weekly patterns get meaningful after about a week.</p>
        </div>
      </section>
    );
  }

  return (
    <section className="analysis card">
      {header}

      <div className="stat-row">
        <StatTile icon="flame" label="Avg calories" value={`${n(s.avg.calories)} kcal`}
                  sub={latest ? `target ${latest.calories.toLocaleString()}` : undefined} />
        <StatTile icon="bolt" label="Avg protein" value={`${n(s.avg.protein_g)} g`}
                  sub={latest ? `target ${latest.protein_g} g` : undefined} />
        <StatTile icon="target" label="Days on target" value={`${s.days_on_target} / ${s.days_logged}`}
                  sub={`kcal ±${rule.calorie_tolerance_pct}% and protein ≥${rule.min_protein_pct}%`} />
        <StatTile icon="drop" label="Avg water" value={s.avg.water_ml ? litres(s.avg.water_ml) : "–"}
                  sub={data.water_target_ml ? `goal ${litres(data.water_target_ml)}` : undefined} />
      </div>
      <p className="muted small">Averages are over the {s.days_logged} day{s.days_logged === 1 ? "" : "s"} with logs, out of {days}.</p>

      <div className="chart-card">
        <h3>Calories per day</h3>
        <BarChart points={pts("calories", (d) => d.targets?.calories ?? null)} color="var(--accent)" unit="kcal"
                  valueLabel="Eaten" ariaLabel="Calories eaten per day compared with the daily target" />
      </div>

      <div className="chart-card">
        <h3>Protein per day</h3>
        <BarChart points={pts("protein_g", (d) => d.targets?.protein_g ?? null)} color="var(--protein)" unit="g"
                  valueLabel="Protein" ariaLabel="Protein per day compared with the daily target" />
      </div>

      <div className="chart-card">
        <h3>Macro trends</h3>
        <LineChart
          labels={labels.map((l) => l.label)} titles={labels.map((l) => l.title)} unit="g"
          ariaLabel="Protein, fiber, carbs and fat in grams per day"
          series={[
            { key: "p", label: "Protein", color: "var(--protein)", values: data.days.map((d) => (d.logged ? d.protein_g : null)) },
            { key: "fi", label: "Fiber", color: "var(--fiber)", values: data.days.map((d) => (d.logged ? d.fiber_g : null)) },
            { key: "c", label: "Carbs", color: "var(--carbs)", values: data.days.map((d) => (d.logged ? d.carbs_g : null)) },
            { key: "f", label: "Fat", color: "var(--fat)", values: data.days.map((d) => (d.logged ? d.fat_g : null)) },
          ]}
        />
      </div>

      <div className="chart-grid-2">
        <div className="chart-card">
          <h3>Where your calories came from</h3>
          <StackedBar
            ariaLabel="Share of calories from protein, carbs and fat"
            segments={[
              { key: "p", label: "Protein", value: s.macro_split_pct.protein ?? 0, color: "var(--protein)" },
              { key: "c", label: "Carbs", value: s.macro_split_pct.carbs ?? 0, color: "var(--carbs)" },
              { key: "f", label: "Fat", value: s.macro_split_pct.fat ?? 0, color: "var(--fat)" },
            ]}
          />
        </div>
        <div className="chart-card">
          <h3>Calories by meal</h3>
          <div className="hbars">
            {(() => {
              const max = Math.max(1, ...MEAL_ORDER.map((m) => s.kcal_by_meal[m] ?? 0));
              return MEAL_ORDER.map((m) => (
                <div key={m} className="hbar-row" title={`${MEAL_LABEL[m]}: ${s.kcal_by_meal[m] ?? 0} kcal`}>
                  <span className="hbar-label">{MEAL_LABEL[m]}</span>
                  <span className="hbar-track"><span className="hbar-fill" style={{ width: `${((s.kcal_by_meal[m] ?? 0) / max) * 100}%` }} /></span>
                  <span className="num hbar-value">{(s.kcal_by_meal[m] ?? 0).toLocaleString()}</span>
                </div>
              ));
            })()}
          </div>
          <p className="muted small">Total kcal per meal over the {days} days.</p>
        </div>
      </div>

      <div className="chart-card">
        <h3>Water per day</h3>
        <BarChart
          points={data.days.map((d, i) => ({ ...labels[i], value: d.water_ml || null, target: data.water_target_ml }))}
          color="var(--water)" unit="ml" valueLabel="Water" ariaLabel="Water per day compared with the daily goal"
        />
      </div>

      <DataTable
        columns={["Date", "kcal", "Protein g", "Fiber g", "Carbs g", "Fat g", "Water ml", "On target"]}
        rows={data.days.map((d, i) => [
          labels[i].title,
          d.logged ? Math.round(d.calories) : "–",
          d.logged ? Math.round(d.protein_g) : "–",
          d.logged ? Math.round(d.fiber_g) : "–",
          d.logged ? Math.round(d.carbs_g) : "–",
          d.logged ? Math.round(d.fat_g) : "–",
          d.water_ml || "–",
          d.on_target == null ? "–" : d.on_target ? "Yes" : "No",
        ])}
      />
    </section>
  );
}
