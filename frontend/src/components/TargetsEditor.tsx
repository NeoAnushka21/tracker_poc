import { useState, type FormEvent } from "react";
import { api } from "../api";
import type { User } from "../types";

type Props = {
  user: User;
  saveLabel: string;
  onSaved: (u: User) => void;
  /** Allow saving even if nothing changed (onboarding "accept" step). */
  alwaysEnabled?: boolean;
};

export default function TargetsEditor({ user, saveLabel, onSaved, alwaysEnabled }: Props) {
  const t = user.targets!;
  const [cal, setCal] = useState(String(t.calories));
  const [protein, setProtein] = useState(String(t.protein_g));
  const [carbs, setCarbs] = useState(String(t.carbs_g));
  const [fat, setFat] = useState(String(t.fat_g));
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const changed =
    Number(cal) !== t.calories || Number(protein) !== t.protein_g ||
    Number(carbs) !== t.carbs_g || Number(fat) !== t.fat_g;
  const macroKcal = Number(protein) * 4 + Number(carbs) * 4 + Number(fat) * 9;

  async function submit(e: FormEvent) {
    e.preventDefault();
    if (!changed) return onSaved(user);
    setBusy(true);
    setError(null);
    try {
      onSaved(await api.updateTargets({
        daily_calorie_target: Math.round(Number(cal)),
        protein_target_g: Math.round(Number(protein)),
        carbs_target_g: Math.round(Number(carbs)),
        fat_target_g: Math.round(Number(fat)),
      }));
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <form onSubmit={submit} className="targets-editor">
      <div className="targets-grid">
        <label>Calories<input type="number" value={cal} onChange={(e) => setCal(e.target.value)} min={800} max={10000} required /></label>
        <label>Protein (g)<input type="number" value={protein} onChange={(e) => setProtein(e.target.value)} min={0} required /></label>
        <label>Carbs (g)<input type="number" value={carbs} onChange={(e) => setCarbs(e.target.value)} min={0} required /></label>
        <label>Fat (g)<input type="number" value={fat} onChange={(e) => setFat(e.target.value)} min={0} required /></label>
      </div>
      <p className={`small ${Math.abs(macroKcal - Number(cal)) > 50 ? "warn" : "muted"}`}>
        Macros add up to {Math.round(macroKcal)} kcal
        {Math.abs(macroKcal - Number(cal)) > 50 && " (doesn't match the calorie target)"}
      </p>
      {error && <p className="error">{error}</p>}
      <button className="primary" disabled={busy || (!alwaysEnabled && !changed)}>{busy ? "Saving…" : saveLabel}</button>
    </form>
  );
}
