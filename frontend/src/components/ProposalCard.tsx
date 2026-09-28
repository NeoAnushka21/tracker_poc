import type { Action, Item } from "../types";
import { MEAL_LABEL, grams, kcal, time } from "../format";

type Props = {
  action: Action;
  busy: boolean;
  awaitingFeedback: boolean;
  onConfirm: () => void;
  onNeedsChanges: () => void;
  onCancel: () => void;
};

const TITLE = { create: "New entry", edit: "Edit entry", delete: "Delete entry" } as const;

const STATUS: Record<Action["status"], string> = {
  pending: "",
  confirmed: "Saved ✓",
  rejected: "Cancelled",
  superseded: "Replaced by a newer version",
  expired: "Expired, not saved",
};

function ItemsTable({ items, struck }: { items: Item[]; struck?: boolean }) {
  return (
    <table className={`items ${struck ? "struck" : ""}`}>
      <thead>
        <tr><th>Item</th><th>Qty</th><th>kcal</th><th>P</th><th>C</th><th>F</th></tr>
      </thead>
      <tbody>
        {items.map((it, i) => (
          <tr key={i}>
            <td>
              {it.ingredient_name}
              {it.brand_name && <span className="muted"> · {it.brand_name}</span>}
            </td>
            <td className="num">{it.quantity} {it.unit}</td>
            <td className="num">{Math.round(it.calories)}</td>
            <td className="num">{grams(it.protein_g)}</td>
            <td className="num">{grams(it.carbs_g)}</td>
            <td className="num">{grams(it.fat_g)}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

export default function ProposalCard({ action, busy, awaitingFeedback, onConfirm, onNeedsChanges, onCancel }: Props) {
  const p = action.payload;
  const pending = action.status === "pending";
  const before = p.before;

  return (
    <div className={`proposal ${action.status} ${awaitingFeedback ? "feedback" : ""}`}>
      <div className="proposal-head">
        <span className="proposal-title">
          {TITLE[action.action_type]}{p.entry_id ? ` #${p.entry_id}` : ""}
        </span>
        {!pending && <span className={`badge ${action.status}`}>{STATUS[action.status]}</span>}
      </div>
      <div className="proposal-summary">{p.summary}</div>

      {action.action_type !== "delete" && p.items && p.totals && (
        <>
          <div className="muted small">
            {MEAL_LABEL[p.meal_type ?? ""] ?? p.meal_type} · {p.eaten_at && time(p.eaten_at)}
            {p.eaten_at && ` on ${p.eaten_at.slice(0, 10)}`}
            {p.meal_type_source === "inferred" && " (meal guessed from time)"}
          </div>
          <ItemsTable items={p.items} />
          <div className="totals">
            <b>{kcal(p.totals.calories)}</b>
            <span>P {grams(p.totals.protein_g)}</span>
            <span>C {grams(p.totals.carbs_g)}</span>
            <span>F {grams(p.totals.fat_g)}</span>
            <span className="muted">Fiber {grams(p.totals.fiber_g)}</span>
          </div>
          {action.action_type === "edit" && before && (
            <div className="muted small">
              Was: {kcal(before.totals.calories)} ({before.items.map((i) => `${i.quantity} ${i.unit} ${i.ingredient_name}`).join(", ")})
            </div>
          )}
        </>
      )}

      {action.action_type === "delete" && before && (
        <>
          <div className="muted small">
            {MEAL_LABEL[before.meal_type] ?? before.meal_type} · {time(before.eaten_at)} on {before.eaten_at.slice(0, 10)} · {kcal(before.totals.calories)}
          </div>
          <ItemsTable items={before.items} struck />
        </>
      )}

      {pending && (
        <div className="proposal-actions">
          <button className="primary" onClick={onConfirm} disabled={busy}>
            {action.action_type === "delete" ? "Yes, delete" : "Looks good"}
          </button>
          <button onClick={onNeedsChanges} disabled={busy}>Needs changes</button>
          <button className="ghost" onClick={onCancel} disabled={busy}>Cancel</button>
        </div>
      )}
    </div>
  );
}
