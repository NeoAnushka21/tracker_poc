import { useState, type ReactNode } from "react";
import type { Action, ActionPayload, Item, Label, Nutrients } from "../types";
import { MEAL_LABEL, grams, kcal, time } from "../format";
import MacroChips from "./MacroChips";

type Props = {
  action: Action;
  /** Just arrived in this session (not loaded from history): springs in. */
  fresh?: boolean;
  busy: boolean;
  awaitingFeedback: boolean;
  onConfirm: () => void;
  onNeedsChanges: () => void;
  onCancel: () => void;
  /** Branded items: the user picked a pack label (code), or "none of these" (null). */
  onPickLabel?: (index: number, code: string | null) => void;
  /** "Find the label" when Open Food Facts didn't answer. */
  onFindLabel?: (index: number) => void;
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
  label: { label: "pack label ✓", hint: "Numbers from the product's pack label (Open Food Facts)" },
  unchecked: { label: "check label", hint: "MacBro's estimate of this product's label. Pick the pack on the card, or check it later in My Foods → Branded" },
};

function tagFor(it: Item): { key: string; label: string; hint: string } | undefined {
  const key = it.source && SOURCE_TAG[it.source] ? it.source : it.brand_name && it.source !== "library" ? "unchecked" : null;
  return key ? { key, ...SOURCE_TAG[key] } : undefined;
}

function ItemsTable({ items, struck }: { items: Item[]; struck?: boolean }) {
  return (
    <table className={`items ${struck ? "struck" : ""}`}>
      <thead>
        <tr><th>Item</th><th>Qty</th><th>kcal</th><th>P</th><th>C</th><th>F</th></tr>
      </thead>
      <tbody>
        {items.map((it, i) => {
          const tag = tagFor(it);
          return (
            <tr key={i}>
              <td>
                {it.ingredient_name}
                {it.brand_name && <span className="muted"> · {it.brand_name}</span>}
                {tag && <span className={`source-tag ${tag.key}`} title={tag.hint}>{tag.label}</span>}
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

/** The bottom line first: calories and protein, big. Everything else waits behind "View details". */
function Hero({ n, caption }: { n: Nutrients; caption?: string }) {
  return (
    <div className="proposal-hero">
      <div className="hero-stat">
        <b className="num">{Math.round(n.calories).toLocaleString()}</b>
        <span>kcal{caption ? ` ${caption}` : ""}</span>
      </div>
      <div className="hero-stat protein">
        <b className="num">{Math.round(n.protein_g)}<small>g</small></b>
        <span><i className="swatch" aria-hidden="true" />protein</span>
      </div>
    </div>
  );
}

/** What MacBro understood, in one dimmed line per item, so it can be checked at a glance. */
function ItemsBrief({ items }: { items: Item[] }) {
  return (
    <ul className="items-brief">
      {items.map((it, i) => {
        const tag = tagFor(it);
        return (
          <li key={i}>
            <span>{it.ingredient_name}{it.brand_name && ` · ${it.brand_name}`}</span>
            <span className="num">{it.quantity} {it.unit}</span>
            {tag && <span className={`source-tag ${tag.key}`} title={tag.hint}>{tag.label}</span>}
          </li>
        );
      })}
    </ul>
  );
}

function LabelLine({ l }: { l: Label }) {
  return (
    <div className="label-product">
      <b>{l.name}</b>{l.brand && <span className="muted"> · {l.brand}</span>}
      <div className="muted small num">
        {[l.pack && `pack ${l.pack}`, `${Math.round(l.calories)} kcal per ${l.ref_qty} ${l.ref_unit}`,
          `P ${l.protein_g} · C ${l.carbs_g} · F ${l.fat_g}`].filter(Boolean).join(" · ")}
      </div>
    </div>
  );
}

/** The pack label for one branded item: the app's best match (or a few) from Open Food Facts, to
 *  pick before Looks good. "Not this one" / "None of these" show the next products; after the last,
 *  MacBro's estimate stays. Nothing is assumed: the label is only used once the user taps it. */
function LabelChoices({ item, busy, onPick, onFind }: {
  item: Item; busy: boolean; onPick: (code: string | null) => void; onFind: () => void;
}) {
  const m = item.label_match!;
  const [page, setPage] = useState(0);
  const [changing, setChanging] = useState(false);
  const name = `${item.brand_name ? `${item.brand_name} ` : ""}${item.ingredient_name}`;
  const picked = m.picked ? m.options.find((o) => o.code === m.picked) : undefined;

  if (picked && !changing) {
    return (
      <div className="label-choice done">
        <span className="label-choice-q">✓ Pack label for <b>{name}</b>{m.how === "barcode" && " (scanned)"}</span>
        <LabelLine l={picked} />
        {item.weight_estimated && <p className="muted tiny">One {item.unit} weighed by MacBro's estimate; the label gives the rest.</p>}
        <button type="button" className="link" disabled={busy} onClick={() => { setChanging(true); setPage(0); }}>Change</button>
      </div>
    );
  }
  if (m.status === "unavailable") {
    return (
      <div className="label-choice">
        <span className="label-choice-q">Couldn't reach Open Food Facts for <b>{name}</b>: MacBro's estimate for now.</span>
        <button type="button" className="link" disabled={busy} onClick={onFind}>Find the label</button>
      </div>
    );
  }
  if (m.status === "none" || !m.options.length) {
    return <p className="label-choice muted small">No pack label found for <b>{name}</b>: MacBro's estimate is used.</p>;
  }
  if (m.declined && !changing) {
    return (
      <p className="label-choice muted small">
        Using MacBro's estimate for <b>{name}</b>.{" "}
        <button type="button" className="link" disabled={busy} onClick={() => { setChanging(true); setPage(0); }}>Show the packs again</button>
      </p>
    );
  }

  // One clear match first ("Is this your pack?"), then three at a time.
  const first = m.status === "sure" && !changing ? 1 : 3;
  const start = page === 0 ? 0 : first + (page - 1) * 3;
  const shown = m.options.slice(start, page === 0 ? first : start + 3);
  const more = start + shown.length < m.options.length;
  const finish = () => { setChanging(false); onPick(null); };
  const choose = (code: string) => { setChanging(false); onPick(code); };
  return (
    <div className="label-choice">
      <span className="label-choice-q">
        {shown.length === 1 && page === 0 && first === 1 ? <>Is this your pack of <b>{name}</b>?</> : <>Which pack is <b>{name}</b>?</>}
      </span>
      <ul className="label-results">
        {shown.map((l) => (
          <li key={l.code}>
            <LabelLine l={l} />
            <button type="button" className="ghost" disabled={busy} onClick={() => choose(l.code)}>
              {shown.length === 1 && first === 1 && page === 0 ? "Yes, this one" : "Use this"}
            </button>
          </li>
        ))}
      </ul>
      <button type="button" className="link" disabled={busy} onClick={() => (more ? setPage(page + 1) : finish())}>
        {more ? (shown.length === 1 ? "Not this one" : "None of these") : "None of these: use MacBro's estimate"}
      </button>
    </div>
  );
}

function Details({ children }: { children: ReactNode }) {
  return (
    <details className="proposal-details">
      <summary>View details</summary>
      {children}
    </details>
  );
}

function Totals({ n, label }: { n: Nutrients; label?: string }) {
  return (
    <div className="totals">
      <MacroChips n={n} label={label ?? "Total"} />
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
      {p.per_ref && <Hero n={p.per_ref} caption={`per ${p.ref_qty} ${p.ref_unit}`} />}
      <div className="muted small">Ingredients for the whole batch · {yieldText(p)}</div>
      {p.ingredients && <ItemsBrief items={p.ingredients} />}
      <Details>
        {p.ingredients && <ItemsTable items={p.ingredients} />}
        {p.per_ref && <Totals n={p.per_ref} label={`Per ${p.ref_qty} ${p.ref_unit}:`} />}
        {p.batch_totals && <div className="muted small">Whole batch: {kcal(p.batch_totals.calories)}</div>}
      </Details>
    </>
  );
}

export default function ProposalCard({ action, fresh, busy, awaitingFeedback, onConfirm, onNeedsChanges, onCancel,
  onPickLabel, onFindLabel }: Props) {
  const p = action.payload;
  const pending = action.status === "pending";
  const before = p.before;
  const isEntry = action.action_type === "create" || action.action_type === "edit";

  return (
    <div className={`proposal ${action.status} ${awaitingFeedback ? "feedback" : ""} ${action.action_type} ${fresh ? "spring-in" : ""}`}>
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
          <Hero n={p.totals} />
          <ItemsBrief items={p.items} />
          {pending && onPickLabel && p.items.map((it, i) => it.label_match && (
            <LabelChoices key={i} item={it} busy={busy} onPick={(code) => onPickLabel(i, code)}
                          onFind={() => onFindLabel?.(i)} />
          ))}
          <Details>
            <ItemsTable items={p.items} />
            <Totals n={p.totals} />
          </Details>
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
          <button className="primary confirm-btn" onClick={onConfirm} disabled={busy}>
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
