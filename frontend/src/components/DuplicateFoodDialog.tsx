import { useEffect, useRef, type ReactNode } from "react";
import type { Food } from "../types";

/** "This product is already in My Foods": shown when a pack label (barcode) picked on Open Food
 *  Facts is already used by another saved food. One label = one saved food. */
export default function DuplicateFoodDialog({ existing, children, actions, onClose }: {
  existing: Food; children?: ReactNode; actions: ReactNode; onClose: () => void;
}) {
  const box = useRef<HTMLDivElement>(null);
  const close = useRef(onClose);
  useEffect(() => { close.current = onClose; });
  // Once, on open: focus the first button; Esc closes.
  useEffect(() => {
    box.current?.querySelector<HTMLButtonElement>("button")?.focus();
    const onKey = (e: KeyboardEvent) => { if (e.key === "Escape") close.current(); };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  return (
    <div className="backdrop">
      <div className="dialog card dup-dialog" role="alertdialog" aria-modal="true" aria-labelledby="dup-title"
           aria-describedby="dup-text" ref={box}>
        <h3 id="dup-title">Already in My Foods</h3>
        <p id="dup-text">
          This product is already saved as <b>{existing.name}{existing.brand_name ? ` · ${existing.brand_name}` : ""}</b>
          {" "}(same pack label, {Math.round(existing.calories)} kcal {existing.measures}). No need to add it again.
        </p>
        {children}
        <div className="dup-actions">{actions}</div>
      </div>
    </div>
  );
}
