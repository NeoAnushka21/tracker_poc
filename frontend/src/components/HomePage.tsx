import { useEffect, useRef, useState } from "react";
import { api } from "../api";
import type { DailySummary, Streak, Streaks, User } from "../types";
import { greeting } from "../format";
import { haptic } from "../haptics";
import { Bar, CalorieRing, Water } from "./Dashboard";
import { AppLogo, MacBroAvatar } from "./Avatar";
import { BOT_NAME } from "../brand";

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

/** A dumbbell, for the protein streak. */
function ProteinIcon() {
  return (
    <svg viewBox="0 0 24 24" width="26" height="26" aria-hidden="true" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
      <path d="M8 12h8" /><rect x="4" y="7" width="4" height="10" rx="1.5" /><rect x="16" y="7" width="4" height="10" rx="1.5" />
      <path d="M2 10v4M22 10v4" />
    </svg>
  );
}

const plural = (n: number) => `${n} day${n === 1 ? "" : "s"}`;

function StreakCard({ kind, s, days, rule, justDone, onCelebrated }: {
  kind: "logging" | "protein"; s: Streak; days: Streaks["last_7_days"]; rule: Streaks["rule"];
  justDone?: boolean; onCelebrated?: () => void;
}) {
  const logging = kind === "logging";
  const hit = (d: Streaks["last_7_days"][number]) => (logging ? d.logged : d.protein_hit);
  const status = s.today_done
    ? "Today counts ✓"
    : logging
      ? s.current > 0 ? "Log a meal today to keep it going" : "Log a meal today to start a streak"
      : s.current > 0 ? `Reach ${rule.min_protein_pct}% of your protein today to extend it`
        : `Reach ${rule.min_protein_pct}% of your protein today to start a streak`;
  return (
    <section className={`streak-card card ${kind} ${s.current > 0 ? "live" : ""} ${justDone ? "celebrate" : ""}`}
             onAnimationEnd={(e) => { if (e.target === e.currentTarget) onCelebrated?.(); }} aria-labelledby={`streak-${kind}`}>
      <div className="streak-top">
        <span className="streak-icon">{logging ? <FlameIcon /> : <ProteinIcon />}</span>
        <div>
          <h3 id={`streak-${kind}`}>{logging ? "Meal logging streak" : "Protein streak"}</h3>
          <p className="muted small">
            {logging ? "Days in a row with at least one meal logged"
              : `Days in a row with at least ${rule.min_protein_pct}% of your protein target`}
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
            <li key={d.date} className={on ? "on" : ""} title={`${label}: ${on ? (logging ? "logged" : "protein reached") : (logging ? "no log" : "protein short")}`}>
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
  // Streaks that went from "not yet today" to done since the last load: they pop once, with a buzz.
  const [justDone, setJustDone] = useState<{ logging: boolean; protein: boolean }>({ logging: false, protein: false });
  const prevStreaks = useRef<Streaks | null>(null);

  useEffect(() => {
    api.daily().then(setDay).catch((e) => setError(e.message));
    api.streaks().then((next) => {
      const prev = prevStreaks.current;
      const flipped = {
        logging: !!prev && !prev.logging.today_done && next.logging.today_done,
        protein: !!prev && !prev.protein.today_done && next.protein.today_done,
      };
      if (flipped.logging || flipped.protein) haptic("celebrate");
      prevStreaks.current = next;
      setJustDone(flipped);
      setStreaks(next);
    }).catch(() => setStreaks(null));
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
        <button type="button" className="macbro-invite" onClick={onOpenChat} aria-label={`Log a meal: chat with ${BOT_NAME}`}>
          <span className="macbro-invite-bubble">Want to log something? <b>Talk to me</b></span>
          <MacBroAvatar size={56} />
        </button>
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
            <StreakCard kind="logging" s={streaks.logging} days={streaks.last_7_days} rule={streaks.rule} justDone={justDone.logging}
                        onCelebrated={() => setJustDone((j) => ({ ...j, logging: false }))} />
            <StreakCard kind="protein" s={streaks.protein} days={streaks.last_7_days} rule={streaks.rule} justDone={justDone.protein}
                        onCelebrated={() => setJustDone((j) => ({ ...j, protein: false }))} />
          </div>
        )}
      </div>
      <p className="muted small health-note">Calories, nutrients and targets are estimates to help you track, not medical advice. <a href="/privacy#health" target="_blank" rel="noopener">More</a></p>
    </div>
  );
}
