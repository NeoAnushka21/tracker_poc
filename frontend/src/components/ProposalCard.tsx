import type { Action, ActionPayload, Item, Nutrients } from "../types";
import { MEAL_LABEL, grams, kcal, time } from "../format";

type Props = {
  action: Action;
  busy: boolean;
  awaitingFeedback: boolean;
  onConfirm: () => void;
  onNeedsChanges: () => void;
  onCancel: () => void;
};

const STATUS: Record<Action["status"], string> = {
  pending: "",
  confirmed: "Saved ✓",
  rejected: "Cancelled",
  superseded: "Replaced by a newer version",
  expired: "Expired, not saved",
};

function title(action: Action): string {
  const p = action.payload;
  switch (action.action_type) {
    case "create": return "New entry";
    case "edit": return `Edit entry #${p.entry_id}`;
    case "delete": return `Delete entry #${p.entry_id}`;
    case "save_recipe": return p.replaces_recipe_id ? "Update recipe" : "New recipe";
    case "water": return "Water";
    case "move": return "Move food";
    case "copy": return "Copy food";
  }
}

const SOURCE_TAG: Record<string, { label: string; hint: string }> = {
  library: { label: "saved", hint: "Numbers from your saved foods" },
  recipe: { label: "recipe", hint: "Numbers from your saved recipe" },
};

function ItemsTable({ items, struck }: { items: Item[]; struck?: boolean }) {
  return (
    <table className={`items ${struck ? "struck" : ""}`}>
      <thead>
        <tr><th>Item</th><th>Qty</th><th>kcal</th><th>P</th><th>C</th><th>F</th></tr>
      </thead>
      <tbody>
        {items.map((it, i) => {
          const tag = it.source ? SOURCE_TAG[it.source] : undefined;
          return (
            <tr key={i}>
              <td>
                {it.ingredient_name}
                {it.brand_name && <span className="muted"> · {it.brand_name}</span>}
                {tag && <span className={`source-tag ${it.source}`} title={tag.hint}>{tag.label}</span>}
              </td>
              <td className="num">{it.quantity} {it.unit}</td>
              <td className="num">{Math.round(it.calories)}</td>
              <td className="num">{grams(it.protein_g)}</td>
              <td className="num">{grams(it.carbs_g)}</td>
              <td className="num">{grams(it.fat_g)}</td>
            </tr>
          );
        })}
      </tbody>
    </table>
  );
}

function Totals({ n, label }: { n: Nutrients; label?: string }) {
  return (
    <div className="totals">
      {label && <span className="muted">{label}</span>}
      <b>{kcal(n.calories)}</b>
      <span>P {grams(n.protein_g)}</span>
      <span>C {grams(n.carbs_g)}</span>
      <span>F {grams(n.fat_g)}</span>
      <span className="muted">Fiber {grams(n.fiber_g)}</span>
    </div>
  );
}

function yieldText(p: ActionPayload): string {
  const parts: string[] = [];
  if (p.yield_pieces) parts.push(`makes ${p.yield_pieces} pieces`);
  if (p.yield_servings) parts.push(`${p.yield_servings} servings`);
  if (p.cooked_weight_g) parts.push(`${p.cooked_weight_g} g cooked`);
  return parts.length ? `Whole batch ${parts.join(", ")}` : "";
}

function RecipeBody({ p }: { p: ActionPayload }) {
  return (
    <>
      <div className="muted small">Ingredients for the whole batch · {yieldText(p)}</div>
      {p.ingredients && <ItemsTable items={p.ingredients} />}
      {p.per_ref && <Totals n={p.per_ref} label={`Per ${p.ref_qty} ${p.ref_unit}:`} />}
      {p.batch_totals && <div className="muted small">Whole batch: {kcal(p.batch_totals.calories)}</div>}
    </>
  );
}

export default function ProposalCard({ action, busy, awaitingFeedback, onConfirm, onNeedsChanges, onCancel }: Props) {
  const p = action.payload;
  const pending = action.status === "pending";
  const before = p.before;
  const isEntry = action.action_type === "create" || action.action_type === "edit";

  return (
    <div className={`proposal ${action.status} ${awaitingFeedback ? "feedback" : ""} ${action.action_type}`}>
      <div className="proposal-head">
        <span className="proposal-title">{title(action)}</span>
        {pending
          ? <span className="badge pending">Not saved yet</span>
          : <span className={`badge ${action.status}`}>{STATUS[action.status]}</span>}
      </div>
      <div className="proposal-summary">{action.action_type === "save_recipe" ? p.name : p.summary}</div>

      {isEntry && p.items && p.totals && (
        <>
          <div className="muted small">
            {MEAL_LABEL[p.meal_type ?? ""] ?? p.meal_type} · {p.eaten_at && time(p.eaten_at)}
            {p.eaten_at && ` on ${p.eaten_at.slice(0, 10)}`}
            {p.meal_type_source === "inferred" && " (meal guessed from time)"}
          </div>
          <ItemsTable items={p.items} />
          <Totals n={p.totals} />
          {action.action_type === "edit" && before && (
            <div className="muted small">
              Was: {kcal(before.totals.calories)} ({before.items.map((i) => `${i.quantity} ${i.unit} ${i.ingredient_name}`).join(", ")})
            </div>
          )}
        </>
      )}

      {action.action_type === "save_recipe" && <RecipeBody p={p} />}

      {(action.action_type === "move" || action.action_type === "copy") && p.items && (
        <>
          <div className="move-route">
            <span className="meal-pill">{MEAL_LABEL[p.from_meal_type ?? ""] ?? p.from_meal_type}</span>
            <span aria-hidden="true">{action.action_type === "copy" ? "⧉ →" : "→"}</span>
            <span className="meal-pill to">{MEAL_LABEL[p.to_meal_type ?? ""] ?? p.to_meal_type}</span>
            {p.to_date && <span className="muted small">on {p.to_date}</span>}
          </div>
          <ItemsTable items={p.items} />
        </>
      )}

      {action.action_type === "water" && p.amount_ml != null && (
        <div className="water-proposal">
          <b>{p.amount_ml.toLocaleString()} ml</b>
          <span className="muted small">{p.drank_at && ` at ${time(p.drank_at)} on ${p.drank_at.slice(0, 10)}`} · added to your water tracker</span>
        </div>
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
            {action.action_type === "delete" ? "Yes, delete"
              : action.action_type === "save_recipe" ? "Save recipe"
              : action.action_type === "water" ? "Log water"
              : action.action_type === "move" ? "Move it"
              : action.action_type === "copy" ? "Copy it" : "Looks good"}
          </button>
          <button onClick={onNeedsChanges} disabled={busy}>Needs changes</button>
          <button className="ghost" onClick={onCancel} disabled={busy}>Cancel</button>
        </div>
      )}
    </div>
  );
}
