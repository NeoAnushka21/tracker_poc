import type { Nutrients } from "../types";
import { grams } from "../format";

const CHIPS = [
  { key: "protein_g", short: "P", label: "Protein", tone: "protein" },
  { key: "carbs_g", short: "C", label: "Carbs", tone: "carbs" },
  { key: "fat_g", short: "F", label: "Fat", tone: "fat" },
  { key: "fiber_g", short: "Fiber", label: "Fiber", tone: "fiber" },
] as const;

/** Bold calories followed by small colour-coded P / C / F / Fiber chips. The letter keeps identity readable without colour. */
export default function MacroChips({ n, label }: { n: Nutrients; label?: string }) {
  return (
    <span className="macro-chips">
      {label && <span className="muted">{label}</span>}
      <b className="kcal-value">{Math.round(n.calories).toLocaleString()} kcal</b>
      {CHIPS.map((c) => (
        <span key={c.key} className={`mchip ${c.tone}`} title={`${c.label}: ${grams(n[c.key])}`}>
          <i aria-hidden="true" />{c.short} {grams(n[c.key])}
        </span>
      ))}
    </span>
  );
}
