import { useState } from "react";
import { applyTheme, getTheme, type ThemeChoice } from "../theme";

const OPTIONS: { id: ThemeChoice; label: string; icon: string }[] = [
  { id: "system", label: "System", icon: "◐" },
  { id: "light", label: "Light", icon: "☀" },
  { id: "dark", label: "Dark", icon: "☾" },
];

export default function ThemeToggle() {
  const [choice, setChoice] = useState<ThemeChoice>(getTheme);

  function pick(c: ThemeChoice) {
    applyTheme(c);
    setChoice(c);
  }

  return (
    <div className="theme-toggle segmented" role="radiogroup" aria-label="Theme">
      {OPTIONS.map((o) => (
        <button
          key={o.id}
          type="button"
          role="radio"
          aria-checked={choice === o.id}
          className={choice === o.id ? "on" : ""}
          onClick={() => pick(o.id)}
          title={`${o.label} theme`}
        >
          <span aria-hidden="true">{o.icon}</span>
          <span className="theme-label">{o.label}</span>
        </button>
      ))}
    </div>
  );
}
