import { useState, type FormEvent } from "react";
import { api } from "../api";
import { ACTIVITY, GOALS } from "../format";
import type { User } from "../types";
import TargetsEditor from "./TargetsEditor";

const LB_PER_KG = 2.20462;
const CM_PER_IN = 2.54;

export default function Onboarding({ onDone }: { onDone: (u: User) => void }) {
  const [units, setUnits] = useState<"metric" | "imperial">("metric");
  const [name, setName] = useState("");
  const [dob, setDob] = useState("");
  const [sex, setSex] = useState<"male" | "female">("male");
  const [heightCm, setHeightCm] = useState("");
  const [feet, setFeet] = useState("");
  const [inches, setInches] = useState("");
  const [weight, setWeight] = useState("");
  const [timezone, setTimezone] = useState(Intl.DateTimeFormat().resolvedOptions().timeZone || "UTC");
  const [goal, setGoal] = useState("weight_loss");
  const [activity, setActivity] = useState("moderate");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<(User & { calculation: { bmr: number; tdee: number } }) | null>(null);

  async function submit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    const height_cm =
      units === "metric" ? Number(heightCm) : (Number(feet) * 12 + Number(inches || 0)) * CM_PER_IN;
    const weight_kg = units === "metric" ? Number(weight) : Number(weight) / LB_PER_KG;
    setBusy(true);
    try {
      const res = await api.onboarding({
        preferred_name: name.trim() || null,
        date_of_birth: dob,
        sex,
        height_cm: Math.round(height_cm * 10) / 10,
        weight_kg: Math.round(weight_kg * 10) / 10,
        unit_system: units,
        timezone: timezone.trim(),
        goal_type: goal,
        activity_level: activity,
      });
      setResult(res);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  if (result) {
    return (
      <div className="center">
        <div className="card onboarding-card">
          <h1>Your daily targets</h1>
          <p className="muted">
            Estimated maintenance: <b>{result.calculation.tdee} kcal/day</b> (BMR {result.calculation.bmr} kcal).
            For your goal ({GOALS[result.goal_type!].toLowerCase()}), here's where I'd start. You can adjust any of these.
          </p>
          <TargetsEditor user={result} saveLabel="Looks good, let's go" onSaved={onDone} alwaysEnabled />
        </div>
      </div>
    );
  }

  return (
    <div className="center">
      <form className="card onboarding-card" onSubmit={submit}>
        <h1>Welcome!</h1>
        <p className="muted">A few details so I can work out your calorie and macro targets.</p>

        <label>
          What should I call you? <span className="muted">(optional)</span>
          <input value={name} onChange={(e) => setName(e.target.value)} placeholder="a name, nickname, 'buddy'…" maxLength={80} />
        </label>

        <div className="row">
          <label>
            Date of birth
            <input type="date" value={dob} onChange={(e) => setDob(e.target.value)} required />
          </label>
          <label>
            Sex <span className="muted">(for the BMR formula)</span>
            <select value={sex} onChange={(e) => setSex(e.target.value as "male" | "female")}>
              <option value="male">Male</option>
              <option value="female">Female</option>
            </select>
          </label>
        </div>

        <div className="segmented" role="radiogroup" aria-label="Units">
          {(["metric", "imperial"] as const).map((u) => (
            <button type="button" key={u} className={units === u ? "on" : ""} onClick={() => setUnits(u)}>
              {u === "metric" ? "Metric (cm, kg)" : "Imperial (ft, lb)"}
            </button>
          ))}
        </div>

        <div className="row">
          {units === "metric" ? (
            <label>
              Height (cm)
              <input type="number" step="0.1" min={50} max={280} value={heightCm} onChange={(e) => setHeightCm(e.target.value)} required />
            </label>
          ) : (
            <label>
              Height
              <span className="row tight">
                <input type="number" min={2} max={9} value={feet} onChange={(e) => setFeet(e.target.value)} placeholder="ft" required />
                <input type="number" min={0} max={11.9} step="0.1" value={inches} onChange={(e) => setInches(e.target.value)} placeholder="in" />
              </span>
            </label>
          )}
          <label>
            Weight ({units === "metric" ? "kg" : "lb"})
            <input type="number" step="0.1" min={20} max={900} value={weight} onChange={(e) => setWeight(e.target.value)} required />
          </label>
        </div>

        <label>
          Goal
          <select value={goal} onChange={(e) => setGoal(e.target.value)}>
            {Object.entries(GOALS).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
          </select>
        </label>

        <label>
          Activity level
          <select value={activity} onChange={(e) => setActivity(e.target.value)}>
            {Object.entries(ACTIVITY).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
          </select>
        </label>

        <label>
          Time zone <span className="muted">(detected from your browser; change it if that's wrong)</span>
          <input value={timezone} onChange={(e) => setTimezone(e.target.value)} required />
        </label>

        {error && <p className="error">{error}</p>}
        <button className="primary" disabled={busy}>{busy ? "Calculating…" : "Calculate my targets"}</button>
      </form>
    </div>
  );
}
