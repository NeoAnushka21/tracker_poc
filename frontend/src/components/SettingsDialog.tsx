import { useState, type FormEvent } from "react";
import { api } from "../api";
import type { User } from "../types";
import TargetsEditor from "./TargetsEditor";

const LB_PER_KG = 2.20462;

type Props = { user: User; onClose: () => void; onSaved: (u: User) => void };

export default function SettingsDialog({ user, onClose, onSaved }: Props) {
  const imperial = user.unit_system === "imperial";
  const [weight, setWeight] = useState("");
  const [recalc, setRecalc] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [msg, setMsg] = useState<string | null>(null);
  const shownWeight = user.weight_kg == null ? "–"
    : imperial ? `${Math.round(user.weight_kg * LB_PER_KG * 10) / 10} lb` : `${user.weight_kg} kg`;

  async function saveWeight(e: FormEvent) {
    e.preventDefault();
    setError(null);
    try {
      const kg = imperial ? Number(weight) / LB_PER_KG : Number(weight);
      const u = await api.logWeight(Math.round(kg * 10) / 10, recalc);
      onSaved(u);
      setWeight("");
      setMsg(recalc ? "Weight saved and targets recalculated." : "Weight saved.");
    } catch (err) {
      setError((err as Error).message);
    }
  }

  return (
    <div className="backdrop" onClick={onClose}>
      <div className="card dialog" onClick={(e) => e.stopPropagation()} role="dialog" aria-modal="true">
        <div className="dialog-head">
          <h2>Targets &amp; weight</h2>
          <button className="ghost" onClick={onClose} aria-label="Close">✕</button>
        </div>

        <h3>Daily targets</h3>
        <TargetsEditor
          key={`${user.targets?.effective_date}-${user.targets?.calories}-${user.targets?.protein_g}`}
          user={user}
          saveLabel="Save targets"
          onSaved={(u) => { onSaved(u); setMsg("Targets saved."); }}
        />

        <h3>Update weight</h3>
        <p className="muted small">Current: {shownWeight}</p>
        <form onSubmit={saveWeight} className="weight-form">
          <input type="number" step="0.1" min={20} max={900} value={weight} onChange={(e) => setWeight(e.target.value)}
                 placeholder={imperial ? "lb" : "kg"} required />
          <label className="check">
            <input type="checkbox" checked={recalc} onChange={(e) => setRecalc(e.target.checked)} />
            Recalculate targets from new weight
          </label>
          <button className="primary">Save weight</button>
        </form>
        {msg && <p className="ok small">{msg}</p>}
        {error && <p className="error">{error}</p>}
      </div>
    </div>
  );
}
