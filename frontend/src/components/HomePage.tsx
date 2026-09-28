import { useEffect, useState } from "react";
import { api } from "../api";
import type { DailySummary, Streak, Streaks, User } from "../types";
import { greeting } from "../format";
import { Bar, CalorieRing, Water } from "./Dashboard";
import { AppLogo } from "./Avatar";

type Props = {
  user: User;
  dataVersion: number;
  onDataChanged: () => void;
  onOpenChat: () => void;
  onOpenDashboard: () => void;
};

function todayLabel(): string {
  return new Date().toLocaleDateString(undefined, { weekday: "long", day: "numeric", month: "long" });
}

/** One line under the greeting, based on how the day is going. */
function subline(d: DailySummary | null): string {
  if (!d?.targets) return "Here's your day at a glance.";
  const eaten = Math.round(d.consumed.calories);
  if (eaten === 0) return "Nothing logged yet today. Log your first meal in Chat.";
  const left = Math.round(d.targets.calories - d.consumed.calories);
  return left >= 0
    ? `${eaten.toLocaleString()} kcal in, ${left.toLocaleString()} kcal to go. Keep it up!`
    : `${eaten.toLocaleString()} kcal in, ${Math.abs(left).toLocaleString()} kcal over target today.`;
}

function FlameIcon() {
  return (
    <svg viewBox="0 0 24 24" width="26" height="26" aria-hidden="true" fill="currentColor">
      <path d="M12 2c1 3.5 5 5.5 5 11a5 5 0 0 1-10 0c0-2.4 1-4 2.5-5.5C9.8 9.8 11 11 12 11c-.5-3 0-6 0-9z" />
    </svg>
  );
}

function TargetIcon() {
  return (
    <svg viewBox="0 0 24 24" width="26" height="26" aria-hidden="true" fill="none" stroke="currentColor" strokeWidth="2">
      <circle cx="12" cy="12" r="9" /><circle cx="12" cy="12" r="5" /><circle cx="12" cy="12" r="1.5" fill="currentColor" />
    </svg>
  );
}

const plural = (n: number) => `${n} day${n === 1 ? "" : "s"}`;

function StreakCard({ kind, s, days, rule }: {
  kind: "logging" | "target"; s: Streak; days: Streaks["last_7_days"]; rule: Streaks["rule"];
}) {
  const logging = kind === "logging";
  const hit = (d: Streaks["last_7_days"][number]) => (logging ? d.logged : d.on_target);
  const status = s.today_done
    ? "Today counts ✓"
    : logging
      ? s.current > 0 ? "Log a meal today to keep it going" : "Log a meal today to start a streak"
      : s.current > 0 ? "Hit today's target to extend it" : "Hit today's target to start a streak";
  return (
    <section className={`streak-card card ${kind} ${s.current > 0 ? "live" : ""}`} aria-labelledby={`streak-${kind}`}>
      <div className="streak-top">
        <span className="streak-icon">{logging ? <FlameIcon /> : <TargetIcon />}</span>
        <div>
          <h3 id={`streak-${kind}`}>{logging ? "Meal logging streak" : "Target streak"}</h3>
          <p className="muted small">
            {logging ? "Days in a row with at least one meal logged"
              : `Days in a row within ±${rule.calorie_tolerance_pct}% of calories with ≥${rule.min_protein_pct}% protein`}
          </p>
        </div>
      </div>
      <div className="streak-count"><b>{s.current}</b> <span>{s.current === 1 ? "day" : "days"}</span></div>
      <p className={`streak-status ${s.today_done ? "ok" : "muted"}`}>{status}</p>
      <ol className="streak-week" aria-label="Last 7 days">
        {days.map((d) => {
          const on = hit(d);
          const label = new Date(`${d.date}T12:00:00`).toLocaleDateString(undefined, { weekday: "short" });
          return (
            <li key={d.date} className={on ? "on" : ""} title={`${label}: ${on ? (logging ? "logged" : "on target") : (logging ? "no log" : "not on target")}`}>
              <span className="dot" aria-hidden="true">{on ? "✓" : ""}</span>
              <span className="day">{label.slice(0, 2)}</span>
              <span className="sr-only">{on ? "yes" : "no"}</span>
            </li>
          );
        })}
      </ol>
      <p className="muted small streak-best">Best: {plural(s.best)}</p>
    </section>
  );
}

/** Landing tab: greeting, today's macros and water, and the two streaks. */
export default function HomePage({ user, dataVersion, onDataChanged, onOpenChat, onOpenDashboard }: Props) {
  const [day, setDay] = useState<DailySummary | null>(null);
  const [streaks, setStreaks] = useState<Streaks | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.daily().then(setDay).catch((e) => setError(e.message));
    api.streaks().then(setStreaks).catch(() => setStreaks(null));
  }, [dataVersion]);

  const t = day?.targets;
  const c = day?.consumed;

  return (
    <div className="home">
      <section className="home-hero card">
        <AppLogo size={64} />
        <div className="home-hero-text">
          <p className="muted small">{todayLabel()}</p>
          <h1>{greeting()}{user.preferred_name ? `, ${user.preferred_name}` : ""}!</h1>
          <p className="muted">{subline(day)}</p>
        </div>
        <button className="primary home-cta" onClick={onOpenChat}>Log a meal</button>
      </section>

      {error && <p className="error">{error}</p>}

      <section className="card home-summary" aria-labelledby="home-summary-title">
        <div className="home-section-head">
          <h2 id="home-summary-title">Today's summary</h2>
          <button className="link" onClick={onOpenDashboard}>Open dashboard →</button>
        </div>
        {!day ? <p className="muted">Loading…</p> : t && c ? (
          <>
            <CalorieRing eaten={c.calories} target={t.calories} />
            <Bar label="Protein" value={c.protein_g} target={t.protein_g} unit="g" tone="protein" />
            <Bar label="Fiber" value={c.fiber_g} target={t.fiber_g} unit="g" tone="fiber" />
            <Bar label="Carbs" value={c.carbs_g} target={t.carbs_g} unit="g" tone="carbs" />
            <Bar label="Fat" value={c.fat_g} target={t.fat_g} unit="g" tone="fat" />
          </>
        ) : <p className="muted">No targets set yet. Add them in Settings → Targets.</p>}
      </section>

      {/* Water gets its own tile; on laptops it sits above the streaks, beside the summary. */}
      <div className="home-side">
        {day?.water && (
          <section className="card home-water"><Water w={day.water} isToday onChanged={onDataChanged} /></section>
        )}
        {streaks && (
          <div className="streaks">
            <StreakCard kind="logging" s={streaks.logging} days={streaks.last_7_days} rule={streaks.rule} />
            <StreakCard kind="target" s={streaks.target} days={streaks.last_7_days} rule={streaks.rule} />
          </div>
        )}
      </div>
    </div>
  );
}
