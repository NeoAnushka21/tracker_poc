import { useEffect, useState } from "react";
import { api } from "../api";
import type { DailySummary } from "../types";

type Props = { dataVersion: number; onOpen: () => void };

/** Today at a glance, shown above the chat so progress stays visible while logging. */
export default function SummaryStrip({ dataVersion, onOpen }: Props) {
  const [data, setData] = useState<DailySummary | null>(null);

  useEffect(() => {
    api.daily().then(setData).catch(() => setData(null));
  }, [dataVersion]);

  if (!data?.targets || !data.remaining) return null;
  const t = data.targets;
  const c = data.consumed;
  const kcalLeft = Math.round(data.remaining.calories);
  const macros = [
    { key: "protein", label: "Protein", value: c.protein_g, target: t.protein_g },
    { key: "carbs", label: "Carbs", value: c.carbs_g, target: t.carbs_g },
    { key: "fat", label: "Fat", value: c.fat_g, target: t.fat_g },
  ];

  return (
    <button className="summary-strip card" onClick={onOpen} title="Open the dashboard">
      <span className="strip-kcal">
        <b className={kcalLeft < 0 ? "warn" : ""}>{Math.abs(kcalLeft).toLocaleString()}</b>
        <span className="muted"> kcal {kcalLeft < 0 ? "over" : "left"} today</span>
      </span>
      <span className="strip-macros">
        {macros.map((m) => {
          const left = Math.round(m.target - m.value);
          const pct = m.target > 0 ? Math.min(100, (m.value / m.target) * 100) : 0;
          return (
            <span key={m.key} className={`strip-macro bar-row ${m.key}`}>
              <span className="strip-macro-label">
                {m.label} <span className={left < 0 ? "warn" : "muted"}>{Math.abs(left)} g {left < 0 ? "over" : "left"}</span>
              </span>
              <span className="bar"><span className={`bar-fill ${left < 0 ? "over" : ""}`} style={{ width: `${pct}%` }} /></span>
            </span>
          );
        })}
      </span>
    </button>
  );
}
