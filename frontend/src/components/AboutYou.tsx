import { useEffect, useState } from "react";
import { api, type PreferenceOptions, type Preferences } from "../api";
import type { User } from "../types";
import { AppLogo } from "./Avatar";

type SuggestedTargets = { daily_calorie_target: number } | null;

/** The optional "about you" questions. Every field can stay empty; `onSkip` (when given) shows
 *  "Skip for now". After saving, if the answers change the calculated calories (pace, pregnancy),
 *  `suggested` is offered; the caller decides whether to show it. */
export function AboutYouForm({ user, saveLabel, onSaved, onSkip }: {
  user: User;
  saveLabel: string;
  onSaved: (u: User, suggested: SuggestedTargets) => void;
  onSkip?: () => void;
}) {
  const [opts, setOpts] = useState<PreferenceOptions | null>(null);
  const [p, setP] = useState<Preferences | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.preferences().then((r) => { setOpts(r.options); setP(r.preferences); }).catch((e) => setError(e.message));
  }, []);

  if (!opts || !p) return <p className="muted">{error ?? "Loading…"}</p>;

  const set = <K extends keyof Preferences>(k: K, v: Preferences[K]) => setP({ ...p, [k]: v });
  const toggle = <T,>(list: T[], v: T) => (list.includes(v) ? list.filter((x) => x !== v) : [...list, v]);
  const paces = opts.pace[user.goal_type ?? ""] ?? [];
  const health = p.health_conditions.length > 0 || p.pregnancy !== null;

  async function save(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const r = await api.savePreferences(p!);
      onSaved(r.user, r.suggested_targets);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <form className="about-you" onSubmit={save}>
      <label>
        Diet
        <select value={p.diet_type ?? ""} onChange={(e) => set("diet_type", e.target.value || null)}>
          <option value="">Not specified</option>
          {Object.entries(opts.diet_types).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
        </select>
      </label>

      <fieldset>
        <legend>Allergies or intolerances</legend>
        <div className="chip-choices">
          {Object.entries(opts.allergens).map(([k, v]) => (
            <button type="button" key={k} className={`chip ${p.allergies.includes(k) ? "on" : ""}`}
                    aria-pressed={p.allergies.includes(k)} onClick={() => set("allergies", toggle(p.allergies, k))}>{v}</button>
          ))}
        </div>
        <input value={p.allergy_notes ?? ""} maxLength={200} placeholder="Anything else? e.g. mushrooms"
               aria-label="Other allergies or intolerances" onChange={(e) => set("allergy_notes", e.target.value || null)} />
      </fieldset>

      {paces.length > 0 && (
        <label>
          How fast? <span className="muted">(sets your calorie target)</span>
          <select value={p.pace_kg_per_week ?? ""} onChange={(e) => set("pace_kg_per_week", e.target.value ? Number(e.target.value) : null)}>
            <option value="">Use the standard for my goal</option>
            {paces.map((v) => <option key={v} value={v}>{v} kg per week</option>)}
          </select>
        </label>
      )}

      <fieldset>
        <legend>Usual meal times <span className="muted">(helps MacBro pick the right meal)</span></legend>
        <div className="row">
          {(["breakfast", "lunch", "dinner"] as const).map((m) => (
            <label key={m}>
              {m[0].toUpperCase() + m.slice(1)}
              <input type="time" value={p[`${m}_time`] ?? ""} onChange={(e) => set(`${m}_time`, e.target.value || null)} />
            </label>
          ))}
        </div>
      </fieldset>

      <fieldset>
        <legend>Training</legend>
        <select value={p.training_type ?? ""} aria-label="Training type" onChange={(e) => set("training_type", e.target.value || null)}>
          <option value="">Not specified</option>
          {Object.entries(opts.training_types).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
        </select>
        <div className="chip-choices" role="group" aria-label="Training days">
          {opts.weekdays.map((d, i) => (
            <button type="button" key={d} className={`chip ${p.training_days.includes(i) ? "on" : ""}`}
                    aria-pressed={p.training_days.includes(i)} onClick={() => set("training_days", toggle(p.training_days, i).sort())}>{d}</button>
          ))}
        </div>
      </fieldset>

      <details className="accordion" open={health}>
        <summary>Health <span className="muted small">(sensitive, entirely optional)</span></summary>
        <fieldset>
          <legend className="sr-only">Health conditions</legend>
          <div className="chip-choices">
            {Object.entries(opts.health_conditions).map(([k, v]) => (
              <button type="button" key={k} className={`chip ${p.health_conditions.includes(k) ? "on" : ""}`}
                      aria-pressed={p.health_conditions.includes(k)} onClick={() => set("health_conditions", toggle(p.health_conditions, k))}>{v}</button>
            ))}
          </div>
          {user.sex === "female" && (
            <label>
              Pregnant or breastfeeding? <span className="muted">(no calorie deficit is set while you are)</span>
              <select value={p.pregnancy ?? ""} onChange={(e) => set("pregnancy", e.target.value || null)}>
                <option value="">No</option>
                {Object.entries(opts.pregnancy).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
              </select>
            </label>
          )}
          {health && (
            <label className="consent-box">
              <input type="checkbox" checked={p.health_consent} onChange={(e) => set("health_consent", e.target.checked)} />
              <span>I agree that these health details are stored and used only to tailor my targets and MacBro's replies (they're sent with my messages to the AI service). MacBro doesn't give medical advice. I can remove them any time.</span>
            </label>
          )}
        </fieldset>
      </details>

      {error && <p className="error">{error}</p>}
      <div className="proposal-actions">
        <button className="primary" disabled={busy}>{busy ? "Saving…" : saveLabel}</button>
        {onSkip && <button type="button" className="ghost" onClick={onSkip} disabled={busy}>Skip for now</button>}
      </div>
    </form>
  );
}

/** "Your calculated target is now … Use it?" after answers that change the formula. */
export function SuggestedTargets({ suggested, user, onDone }: {
  suggested: NonNullable<SuggestedTargets>; user: User; onDone: (u: User | null) => void;
}) {
  const [busy, setBusy] = useState(false);
  return (
    <div className="card suggest-targets" role="status">
      <p>
        With these answers your calculated target is <b>{suggested.daily_calorie_target.toLocaleString()} kcal</b> a day
        {user.targets ? <> (now {user.targets.calories.toLocaleString()} kcal)</> : null}. Use it?
      </p>
      <div className="proposal-actions">
        <button className="primary" disabled={busy}
                onClick={async () => { setBusy(true); onDone(await api.recalculateTargets()); }}>Use the new target</button>
        <button className="ghost" disabled={busy} onClick={() => onDone(null)}>Keep mine</button>
      </div>
    </div>
  );
}

/** Once, for accounts that haven't answered or skipped yet (after onboarding and country). */
export function AboutYouGate({ user, onDone, onLogout }: { user: User; onDone: (u: User) => void; onLogout: () => void }) {
  const [saved, setSaved] = useState<{ user: User; suggested: NonNullable<SuggestedTargets> } | null>(null);
  return (
    <div className="center">
      <div className="card onboarding-card">
        <div className="auth-brand">
          <AppLogo size={56} />
          <div>
            <h1>A bit more about you</h1>
            <p className="muted">All optional. Answer what you like, skip the rest, and change it any time in Settings → About you.</p>
          </div>
        </div>
        {saved ? (
          <SuggestedTargets suggested={saved.suggested} user={saved.user} onDone={(u) => onDone(u ?? saved.user)} />
        ) : (
          <AboutYouForm user={user} saveLabel="Save and continue"
                        onSaved={(u, s) => (s ? setSaved({ user: u, suggested: s }) : onDone(u))}
                        onSkip={async () => onDone(await api.skipPreferences())} />
        )}
        <button type="button" className="link" onClick={onLogout}>Log out instead</button>
      </div>
    </div>
  );
}
