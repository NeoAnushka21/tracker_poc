import { useEffect, useState, type FormEvent } from "react";
import { api, type BodyProfileData } from "../api";
import type { User } from "../types";

const LB_PER_KG = 2.20462;
const CM_PER_IN = 2.54;

function when(iso: string | null): string {
  return iso ? new Date(iso).toLocaleDateString(undefined, { day: "numeric", month: "short", year: "numeric" }) : "–";
}

type Props = { user: User; onUserChanged: (u: User) => void };

/** Settings → Body profile: weight and height (required), plus optional dated measurements. */
export default function BodyProfile({ user, onUserChanged }: Props) {
  const imperial = user.unit_system === "imperial";
  const len = (cm: number) => (imperial ? `${(cm / CM_PER_IN).toFixed(1)} in` : `${cm} cm`);
  const lenDelta = (cm: number) => (imperial ? `${Math.abs(cm / CM_PER_IN).toFixed(1)} in` : `${Math.abs(cm)} cm`);
  const toCm = (v: string) => (imperial ? Number(v) * CM_PER_IN : Number(v));
  const kg = (v: number) => (imperial ? `${(v * LB_PER_KG).toFixed(1)} lb` : `${v} kg`);

  const [data, setData] = useState<BodyProfileData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [msg, setMsg] = useState<string | null>(null);
  const [weight, setWeight] = useState("");
  const [height, setHeight] = useState("");
  const [recalc, setRecalc] = useState(true);
  const [parts, setParts] = useState<Record<string, string>>({});
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    api.getBody().then(setData).catch((e) => setError(e.message));
  }, []);

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

  function saveWeight(e: FormEvent) {
    e.preventDefault();
    const value = imperial ? Number(weight) / LB_PER_KG : Number(weight);
    run(async () => {
      onUserChanged(await api.logWeight(Math.round(value * 10) / 10, recalc));
      setWeight("");
      setData(await api.getBody());
    }, recalc ? "Weight saved and targets recalculated." : "Weight saved.");
  }

  function saveHeight(e: FormEvent) {
    e.preventDefault();
    run(async () => {
      onUserChanged(await api.updateHeight(Math.round(toCm(height) * 10) / 10, recalc));
      setHeight("");
      setData(await api.getBody());
    }, recalc ? "Height saved and targets recalculated." : "Height saved.");
  }

  function saveParts(e: FormEvent) {
    e.preventDefault();
    const body: Record<string, number> = {};
    for (const [k, v] of Object.entries(parts)) if (v.trim()) body[k] = Math.round(toCm(v) * 10) / 10;
    if (!Object.keys(body).length) return setError("Enter at least one measurement.");
    run(async () => {
      setData(await api.addMeasurements(body));
      setParts({});
    }, "Measurements saved.");
  }

  if (!data) return error ? <p className="error">{error}</p> : <p className="muted">Loading…</p>;

  return (
    <div className="body-profile">
      <h3 className="first">Weight &amp; height</h3>
      <div className="body-stats">
        <div className="stat-tile">
          <div className="stat-label">Current weight</div>
          <div className="stat-value">{data.weight_kg != null ? kg(data.weight_kg) : "–"}</div>
          {data.weight_history[1] && (
            <div className="stat-sub">
              {(() => {
                const d = Math.round((data.weight_history[0].weight_kg - data.weight_history[1].weight_kg) * 10) / 10;
                return d === 0 ? "no change" : `${d > 0 ? "▲" : "▼"} ${kg(Math.abs(d))} since ${when(data.weight_history[1].logged_at)}`;
              })()}
            </div>
          )}
        </div>
        <div className="stat-tile">
          <div className="stat-label">Height</div>
          <div className="stat-value">{data.height_cm != null ? len(data.height_cm) : "–"}</div>
        </div>
      </div>

      <div className="body-forms">
        <form onSubmit={saveWeight} className="inline-form">
          <label>New weight ({imperial ? "lb" : "kg"})
            <input type="number" step="0.1" min={20} max={900} value={weight} onChange={(e) => setWeight(e.target.value)} required />
          </label>
          <button className="primary" disabled={busy}>Save weight</button>
        </form>
        <form onSubmit={saveHeight} className="inline-form">
          <label>New height ({imperial ? "in" : "cm"})
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

      <h3>Body measurements <span className="muted small">(optional)</span></h3>
      <p className="muted small">Add any you like, whenever you like. Each save is dated so you can see progress.</p>
      <div className="table-scroll">
        <table className="measure-table">
          <thead><tr><th>Measurement</th><th>Latest</th><th>Change</th><th>Measured</th></tr></thead>
          <tbody>
            {data.latest.map((p) => (
              <tr key={p.key}>
                <td>{p.label}</td>
                <td className="num">{p.value_cm != null ? len(p.value_cm) : <span className="muted">–</span>}</td>
                <td className="num">
                  {p.change_cm == null ? <span className="muted">–</span>
                    : p.change_cm === 0 ? "no change"
                    : `${p.change_cm > 0 ? "▲" : "▼"} ${lenDelta(p.change_cm)}`}
                </td>
                <td className="muted">{when(p.measured_at)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <form onSubmit={saveParts} className="measure-form">
        <div className="measure-grid">
          {data.latest.map((p) => (
            <label key={p.key}>{p.label} ({imperial ? "in" : "cm"})
              <input type="number" step="0.1" min={imperial ? 4 : 10} max={imperial ? 100 : 250}
                     value={parts[p.key] ?? ""} placeholder="optional"
                     onChange={(e) => setParts({ ...parts, [p.key]: e.target.value })} />
            </label>
          ))}
        </div>
        <button className="primary" disabled={busy}>Save measurements</button>
      </form>

      {msg && <p className="ok small">{msg}</p>}
      {error && <p className="error">{error}</p>}

      {data.history.length > 0 && (
        <details className="chart-table">
          <summary>Measurement history ({data.history.length})</summary>
          <ul className="measure-history">
            {data.history.map((h) => (
              <li key={h.id}>
                <span className="muted">{when(h.measured_at)}</span>
                <span>
                  {data.latest.filter((p) => h[p.key] != null).map((p) => `${p.label} ${len(h[p.key] as number)}`).join(" · ")}
                </span>
                <button type="button" className="ghost danger" disabled={busy}
                        onClick={() => window.confirm("Delete this set of measurements?") &&
                          run(async () => setData(await api.deleteMeasurement(h.id)), "Deleted.")}>
                  Delete
                </button>
              </li>
            ))}
          </ul>
        </details>
      )}
    </div>
  );
}
