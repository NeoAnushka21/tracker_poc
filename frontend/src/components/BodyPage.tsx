import { useEffect, useRef, useState, type FormEvent } from "react";
import { api, type BodyFat, type BodyProfileData } from "../api";
import type { User } from "../types";
import { BodyCallouts, BodyDots, type FigurePart } from "./BodyFigure";

const LB_PER_KG = 2.20462;
const CM_PER_IN = 2.54;

function when(iso: string | null): string {
  return iso ? new Date(iso).toLocaleDateString(undefined, { day: "numeric", month: "short", year: "numeric" }) : "–";
}

const joinAnd = (xs: string[]) => (xs.length < 2 ? xs.join("") : `${xs.slice(0, -1).join(", ")} and ${xs[xs.length - 1]}`);

/** What the body-fat tile says: a number only when the formula has everything it needs. */
function fatText(f: BodyFat): { value: string; sub: string } {
  if (f.status === "ok") return { value: `≈ ${f.value}%`, sub: `US Navy method · ±${f.typical_error} points` };
  if (f.status === "missing") return { value: "–", sub: `Not enough info to estimate: add your ${joinAnd(f.missing)}.` };
  return { value: "–", sub: f.reason };
}

type Props = { user: User; onUserChanged: (u: User) => void };

/** Body Profile tab: weight, height, BMI and body fat, plus a body diagram to add optional, dated measurements. */
export default function BodyPage({ user, onUserChanged }: Props) {
  const imperial = user.unit_system === "imperial";
  const unit = imperial ? "in" : "cm";
  const len = (cm: number) => (imperial ? `${(cm / CM_PER_IN).toFixed(1)} in` : `${cm} cm`);
  const lenDelta = (cm: number) => (imperial ? `${Math.abs(cm / CM_PER_IN).toFixed(1)} in` : `${Math.abs(cm)} cm`);
  const toCm = (v: string) => Math.round((imperial ? Number(v) * CM_PER_IN : Number(v)) * 10) / 10;
  const fromCm = (cm: number) => String(imperial ? Math.round((cm / CM_PER_IN) * 10) / 10 : cm);
  const kg = (v: number) => (imperial ? `${(v * LB_PER_KG).toFixed(1)} lb` : `${v} kg`);
  const change = (cm: number | null) => (cm == null ? null : cm === 0 ? "no change" : `${cm > 0 ? "▲" : "▼"} ${lenDelta(cm)}`);

  const [data, setData] = useState<BodyProfileData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [msg, setMsg] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [weight, setWeight] = useState("");
  const [height, setHeight] = useState("");
  const [recalc, setRecalc] = useState(true);
  const [selected, setSelected] = useState<string | null>(null);
  const [value, setValue] = useState("");
  const [editing, setEditing] = useState<{ id: number; values: Record<string, string> } | null>(null);
  const editorRef = useRef<HTMLDivElement>(null);

  // On phones the editor sits below the list: bring it into view when a part is picked.
  useEffect(() => {
    if (selected) editorRef.current?.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }, [selected]);

  useEffect(() => {
    api.getBody().then(setData).catch((e) => setError(e.message));
  }, [user.sex, user.height_cm]);

  async function run(fn: () => Promise<void>, done: string) {
    setBusy(true);
    setError(null);
    setMsg(null);
    try {
      await fn();
      setMsg(done);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  function select(key: string) {
    setSelected(key === selected ? null : key);
    setValue("");
    setMsg(null);
  }

  function savePart(e: FormEvent) {
    e.preventDefault();
    if (!selected || !value.trim()) return;
    const label = data?.latest.find((p) => p.key === selected)?.label ?? "Measurement";
    run(async () => {
      setData(await api.addMeasurements({ [selected]: toCm(value) }));
      setValue("");
    }, `${label} saved.`);
  }

  function saveWeight(e: FormEvent) {
    e.preventDefault();
    const v = imperial ? Number(weight) / LB_PER_KG : Number(weight);
    run(async () => {
      onUserChanged(await api.logWeight(Math.round(v * 10) / 10, recalc));
      setWeight("");
      setData(await api.getBody());
    }, recalc ? "Weight saved and targets recalculated." : "Weight saved.");
  }

  function saveHeight(e: FormEvent) {
    e.preventDefault();
    run(async () => {
      onUserChanged(await api.updateHeight(toCm(height), recalc));
      setHeight("");
      setData(await api.getBody());
    }, recalc ? "Height saved and targets recalculated." : "Height saved.");
  }

  function saveEdit(e: FormEvent) {
    e.preventDefault();
    if (!editing) return;
    const body: Record<string, number | null> = {};
    for (const p of data?.latest ?? []) {
      const s = editing.values[p.key]?.trim();
      body[p.key] = s ? toCm(s) : null;
    }
    run(async () => {
      setData(await api.editMeasurement(editing.id, body));
      setEditing(null);
    }, "Measurement corrected.");
  }

  if (!data) return error ? <p className="error">{error}</p> : <p className="muted">Loading…</p>;

  const sex = data.sex === "female" ? "female" : "male";
  const parts: FigurePart[] = data.latest.map((p) => ({
    key: p.key, label: p.label, value: p.value_cm != null ? len(p.value_cm) : null, change: change(p.change_cm),
  }));
  const current = data.latest.find((p) => p.key === selected) ?? null;
  const fat = fatText(data.body_fat);
  const prevWeight = data.weight_history[1];
  const status = (
    <>
      {msg && <p className="ok small">{msg}</p>}
      {error && <p className="error small">{error}</p>}
    </>
  );

  return (
    <div className="body-page">
      <section className="card">
        <h2>Body Profile</h2>
        <p className="muted small">Your current numbers. Measurements are optional: add any you like, whenever you like.</p>
        <div className="body-stats-row">
          <div className="stat-tile">
            <div className="stat-label">Weight</div>
            <div className="stat-value">{data.weight_kg != null ? kg(data.weight_kg) : "–"}</div>
            {prevWeight && data.weight_kg != null && (
              <div className="stat-sub">
                {(() => {
                  const d = Math.round((data.weight_kg - prevWeight.weight_kg) * 10) / 10;
                  return d === 0 ? "no change" : `${d > 0 ? "▲" : "▼"} ${kg(Math.abs(d))} since ${when(prevWeight.logged_at)}`;
                })()}
              </div>
            )}
          </div>
          <div className="stat-tile">
            <div className="stat-label">Height</div>
            <div className="stat-value">{data.height_cm != null ? len(data.height_cm) : "–"}</div>
            <div className="stat-sub">{data.sex === "female" ? "Female" : data.sex === "male" ? "Male" : ""}</div>
          </div>
          <div className="stat-tile">
            <div className="stat-label">BMI</div>
            {data.bmi.status === "ok" ? (
              <>
                <div className="stat-value">{data.bmi.value}</div>
                <div className={`bmi-chip ${data.bmi.category.split(" ")[0].toLowerCase()}`}>{data.bmi.category}</div>
              </>
            ) : (
              <>
                <div className="stat-value">–</div>
                <div className="stat-sub">Add your {joinAnd(data.bmi.missing)}.</div>
              </>
            )}
          </div>
          <div className="stat-tile">
            <div className="stat-label">Body fat (estimate)</div>
            <div className="stat-value">{fat.value}</div>
            <div className="stat-sub">{fat.sub}</div>
            {data.body_fat.status === "ok" && data.body_fat.warning && <div className="stat-sub warn">{data.body_fat.warning}</div>}
          </div>
        </div>
        <details className="about-numbers">
          <summary>About these numbers</summary>
          <p className="muted small">
            <b>BMI</b> is weight (kg) ÷ height (m)², with the WHO adult categories: under 18.5 underweight, 18.5–24.9 healthy
            weight, 25–29.9 overweight, 30 and over obesity. It doesn't tell muscle from fat.
          </p>
          <p className="muted small">
            <b>Body fat</b> uses the US Navy tape-measure equations (Hodgdon &amp; Beckett, 1984) with your height, neck and
            waist (and hips for women). It's typically within about ±3–4 percentage points of lab methods when the
            measurements are taken as described in each tip, at the same time of day. If something is missing or the
            numbers don't add up, no estimate is shown rather than a guess. These are estimates, not medical advice.
          </p>
        </details>
      </section>

      <section className="card body-diagram">
        <h3 className="first">Measurements</h3>
        <p className="muted small">Tap a body part to add a measurement. Each save is dated, so you can see how it changes.</p>
        <div className="bd-layout">
          <div className="bd-figure">
            <BodyCallouts sex={sex} parts={parts} selected={selected} onSelect={select} />
            <BodyDots sex={sex} keys={parts.map((p) => p.key)} selected={selected} onSelect={select} />
            <ol className="bd-list">
              {parts.map((p) => (
                <li key={p.key}>
                  <button type="button" className={selected === p.key ? "on" : ""} onClick={() => select(p.key)}>
                    <span className="bd-name">{p.label}</span>
                    <span className="num">{p.value ?? <span className="muted">+ Add</span>}</span>
                    {p.change && <span className="muted small">{p.change}</span>}
                  </button>
                </li>
              ))}
            </ol>
          </div>
          <div className="bd-editor" aria-live="polite" ref={editorRef}>
            {current ? (
              <form onSubmit={savePart}>
                <h4>{current.label}</h4>
                <p className="muted small">{current.tip}</p>
                <p className="small">
                  {current.value_cm != null
                    ? <>Latest <b>{len(current.value_cm)}</b>{current.change_cm != null && ` (${change(current.change_cm)})`} · {when(current.measured_at)}</>
                    : <span className="muted">Not measured yet.</span>}
                </p>
                <label>New {current.label.toLowerCase()} ({unit})
                  <input type="number" step="0.1" min={imperial ? 2 : 5} max={imperial ? 100 : 250} value={value} autoFocus
                         onChange={(e) => setValue(e.target.value)} required />
                </label>
                <div className="row tight">
                  <button className="primary" disabled={busy}>Save</button>
                  <button type="button" className="ghost" onClick={() => setSelected(null)}>Close</button>
                </div>
                {status}
              </form>
            ) : (
              <p className="muted small bd-hint">Pick a body part to see how to measure it and add a value.
                For a body-fat estimate you need neck and waist{sex === "female" ? ", plus hips" : ""}.</p>
            )}
          </div>
        </div>
      </section>

      <section className="card">
        <h3 className="first">Update weight &amp; height</h3>
        <div className="body-forms">
          <form onSubmit={saveWeight} className="inline-form">
            <label>New weight ({imperial ? "lb" : "kg"})
              <input type="number" step="0.1" min={20} max={900} value={weight} onChange={(e) => setWeight(e.target.value)} required />
            </label>
            <button className="primary" disabled={busy}>Save weight</button>
          </form>
          <form onSubmit={saveHeight} className="inline-form">
            <label>New height ({unit})
              <input type="number" step="0.1" min={imperial ? 20 : 50} max={imperial ? 110 : 280} value={height}
                     onChange={(e) => setHeight(e.target.value)} required />
            </label>
            <button className="primary" disabled={busy}>Save height</button>
          </form>
        </div>
        <label className="check">
          <input type="checkbox" checked={recalc} onChange={(e) => setRecalc(e.target.checked)} />
          Recalculate my calorie and macro targets when weight or height changes
        </label>
        {!selected && status}
      </section>

      {data.history.length > 0 && (
        <section className="card">
          <h3 className="first">Measurement history <span className="muted small">({data.history.length})</span></h3>
          <p className="muted small">To record a new value, use the diagram. Edit here only to fix a mistake in a saved entry.</p>
          <ul className="measure-history">
            {data.history.map((h) => (
              <li key={h.id}>
                <span className="muted">{when(h.measured_at)}</span>
                {editing?.id === h.id ? (
                  <form className="measure-edit" onSubmit={saveEdit}>
                    <div className="measure-grid">
                      {data.latest.map((p) => (
                        <label key={p.key}>{p.label} ({unit})
                          <input type="number" step="0.1" min={imperial ? 2 : 5} max={imperial ? 100 : 250}
                                 value={editing.values[p.key] ?? ""} placeholder="–"
                                 onChange={(e) => setEditing({ ...editing, values: { ...editing.values, [p.key]: e.target.value } })} />
                        </label>
                      ))}
                    </div>
                    <div className="row tight">
                      <button className="primary" disabled={busy}>Save</button>
                      <button type="button" className="ghost" onClick={() => setEditing(null)}>Cancel</button>
                    </div>
                  </form>
                ) : (
                  <span>{data.latest.filter((p) => h[p.key] != null).map((p) => `${p.label} ${len(h[p.key] as number)}`).join(" · ")}</span>
                )}
                {editing?.id !== h.id && (
                  <span className="row tight">
                    <button type="button" className="ghost" disabled={busy} onClick={() => setEditing({
                      id: h.id,
                      values: Object.fromEntries(data.latest.filter((p) => h[p.key] != null).map((p) => [p.key, fromCm(h[p.key] as number)])),
                    })}>Edit</button>
                    <button type="button" className="ghost danger" disabled={busy}
                            onClick={() => window.confirm("Delete this set of measurements?") &&
                              run(async () => setData(await api.deleteMeasurement(h.id)), "Deleted.")}>
                      Delete
                    </button>
                  </span>
                )}
              </li>
            ))}
          </ul>
        </section>
      )}
    </div>
  );
}
