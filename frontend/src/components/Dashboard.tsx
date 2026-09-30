import { useEffect, useState, type SyntheticEvent } from "react";
import { api } from "../api";
import type { Action, DailySummary, Entry, Food, Item, MicroSummary, WaterSummary } from "../types";
import { MEAL_LABEL, MEAL_ORDER, friendlyDate, grams, litres, shiftDay } from "../format";
import { haptic } from "../haptics";
import { useRevealFill } from "../motion";
import AnalysisPage from "./AnalysisPage";
import MacBroInvite from "./MacBroInvite";
import MacroChips from "./MacroChips";
import {
  AppleIcon, ArrowRightIcon, BowlIcon, ChatIcon, ChevronDownIcon, CloseIcon, CupIcon, MoonIcon, PencilIcon,
  SunriseIcon, TrashIcon, TrendIcon, WaterDrop,
} from "./icons";

/** How a macro stands against its target. Protein and fiber are goals: going past is good.
 *  Carbs and fat are budgets: 100-105% counts as hitting the target, beyond that is over. */
export function macroState(tone: string, value: number, target: number): "reached" | "over" | "under" {
  if (target <= 0 || value < target) return "under";
  if (tone === "protein" || tone === "fiber") return "reached";
  return value <= target * 1.05 ? "reached" : "over";
}

/** A meter: one macro against its target. Identity comes from the label; the fill hue repeats it.
 *  Reaching the target swaps the flat fill for a slow-moving gradient, as a small reward. */
export function Bar({ label, value, target, unit, tone }: {
  label: string; value: number; target: number; unit: string; tone: "protein" | "fiber" | "carbs" | "fat";
}) {
  const pct = target > 0 ? Math.min(100, (value / target) * 100) : 0;
  const [ref, shownPct] = useRevealFill<HTMLDivElement>(pct);
  const left = Math.round(target - value);
  const state = macroState(tone, value, target);
  const goal = tone === "protein" || tone === "fiber";
  return (
    <div className={`bar-row ${tone}`} title={`${label}: ${Math.round(value)} of ${target} ${unit}`}>
      <div className="bar-label">
        <span className="bar-name"><i className="swatch" aria-hidden="true" />{label}</span>
        <span className="num">
          {Math.round(value)} / {target} {unit}
          <span className={state === "over" ? "warn" : state === "reached" ? "ok" : "muted"}>
            {" · "}{state === "reached" ? (goal ? "goal met ✓" : "on target ✓")
              : state === "over" ? `${-left} ${unit} over` : `${left} ${unit} left`}
          </span>
        </span>
      </div>
      <div className="bar" ref={ref} role="progressbar" aria-valuenow={Math.round(value)} aria-valuemax={target} aria-label={label}>
        <div className={`bar-fill ${state === "under" ? "" : state}`} style={{ width: `${shownPct}%` }} />
      </div>
    </div>
  );
}

/** Dashboard summary: one compact meter (label, eaten / target, a thin bar, what's left).
 *  The big ring and bars live on Home; here the day fits in one small tile. */
function Stat({ label, value, target, unit, tone }: {
  label: string; value: number; target: number; unit: string; tone: "kcal" | "protein" | "fiber" | "carbs" | "fat";
}) {
  const pct = target > 0 ? Math.min(100, (value / target) * 100) : 0;
  const [ref, shownPct] = useRevealFill<HTMLDivElement>(pct);
  const state = tone === "kcal" ? (value > target ? "over" : "under") : macroState(tone, value, target);
  const left = Math.round(target - value);
  const goal = tone === "protein" || tone === "fiber";
  return (
    <div className={`stat ${tone} ${state}`}>
      <span className="stat-label"><i className="swatch" aria-hidden="true" />{label}</span>
      <span className="stat-value num">
        <b>{Math.round(value).toLocaleString()}</b><span className="muted"> / {target.toLocaleString()} {unit}</span>
      </span>
      <div className="bar stat-bar" ref={ref} role="progressbar" aria-label={label}
           aria-valuenow={Math.round(value)} aria-valuemax={target}>
        <div className={`bar-fill ${state === "under" ? "" : state}`} style={{ width: `${shownPct}%` }} />
      </div>
      <span className={`stat-note ${state === "over" ? "warn" : state === "reached" ? "ok" : "muted"}`}>
        {state === "reached" ? (goal ? "goal met ✓" : "on target ✓")
          : state === "over" ? `${(-left).toLocaleString()} ${unit} over` : `${left.toLocaleString()} ${unit} left`}
      </span>
    </div>
  );
}

/** Calorie meter as a ring: remaining kcal is the headline, eaten/target beside it. */
export function CalorieRing({ eaten, target }: { eaten: number; target: number }) {
  const r = 52;
  const circumference = 2 * Math.PI * r;
  const [ref, frac] = useRevealFill<SVGSVGElement>(target > 0 ? Math.min(1, eaten / target) : 0);
  const remaining = Math.round(target - eaten);
  const over = remaining < 0;
  return (
    <div className="kcal-ring-wrap">
      <svg ref={ref} className={`kcal-ring ${over ? "over" : ""}`} viewBox="0 0 120 120" role="img"
           aria-label={`${Math.round(eaten)} of ${target} kcal eaten`}>
        <title>{`${Math.round(eaten)} of ${target} kcal eaten`}</title>
        <circle className="ring-track" cx="60" cy="60" r={r} />
        <circle className="ring-fill" cx="60" cy="60" r={r}
                strokeDasharray={`${frac * circumference} ${circumference}`}
                transform="rotate(-90 60 60)"
                style={frac > 0 ? undefined : { opacity: 0 }} /* a zero-length stroke still draws its round cap */ />
        <text x="60" y="57" className="ring-value">{Math.round(eaten).toLocaleString()}</text>
        <text x="60" y="75" className="ring-caption">/ {target.toLocaleString()} kcal</text>
      </svg>
      <dl className="kcal-stats">
        <div>
          <dt>{over ? "Over budget by" : "Balance"}</dt>
          <dd className={over ? "warn" : ""}>{Math.abs(remaining).toLocaleString()} kcal</dd>
        </div>
        <div><dt>Progress</dt><dd>{target > 0 ? Math.round((eaten / target) * 100) : 0}%</dd></div>
      </dl>
    </div>
  );
}

function fmtMicro(v: number): string {
  return v >= 100 ? Math.round(v).toLocaleString() : String(Math.round(v * 10) / 10);
}

const MICROS_OPEN_KEY = "micros-open";

/** Secondary panel, folded by default so the day's main goals stay on top; the choice is remembered
 *  on this device. One muted hue for every nutrient; the label carries identity. */
function Micronutrients({ m }: { m: MicroSummary }) {
  const [open, setOpen] = useState(() => {
    try { return localStorage.getItem(MICROS_OPEN_KEY) === "1"; } catch { return false; }
  });
  function toggle(e: SyntheticEvent<HTMLDetailsElement>) {
    const now = e.currentTarget.open;
    setOpen(now);
    try { localStorage.setItem(MICROS_OPEN_KEY, now ? "1" : "0"); } catch { /* not remembered, that's fine */ }
  }
  const low = m.nutrients.filter((n) => n.kind !== "limit" && n.target > 0 && n.consumed < n.target * 0.5).length;
  const over = m.nutrients.filter((n) => n.kind === "limit" && n.consumed > n.target).length;
  return (
    <details className="micros accordion" open={open} onToggle={toggle}>
      <summary>
        <span className="accordion-title">Additional micronutrients</span>
        <span className="muted small">
          {m.nutrients.length} tracked{over > 0 ? ` · ${over} over limit` : low > 0 ? ` · ${low} under half` : ""}
        </span>
      </summary>
      <p className="muted small">
        Approximate: estimated by the assistant from typical food data.
        {m.items_total > 0 && m.items_with_data < m.items_total &&
          ` ${m.items_with_data} of ${m.items_total} items today have estimates (older entries don't).`}
      </p>
      <div className="micro-grid">
        {m.nutrients.map((n) => {
          const pct = n.target > 0 ? Math.min(100, (n.consumed / n.target) * 100) : 0;
          const over = n.kind === "limit" && n.consumed > n.target;
          return (
            <div key={n.key} className={`micro ${n.kind}`} title={`${n.label}: ${fmtMicro(n.consumed)} of ${n.target} ${n.unit}`}>
              <div className="micro-label">
                <span>{n.label}{n.kind === "limit" && <span className="muted"> (limit)</span>}</span>
                <span className={`num ${over ? "warn" : ""}`}>
                  {fmtMicro(n.consumed)} / {n.target.toLocaleString()} {n.unit}
                </span>
              </div>
              <div className="bar" role="progressbar" aria-label={n.label}
                   aria-valuenow={Math.round(n.consumed)} aria-valuemax={n.target}>
                <div className={`bar-fill ${over ? "over" : ""}`} style={{ width: `${pct}%` }} />
              </div>
            </div>
          );
        })}
      </div>
    </details>
  );
}

/** Independent water tracker: quick-add buttons save directly (they're the user's own clicks). */
export function Water({ w, isToday, onChanged }: { w: WaterSummary; isToday: boolean; onChanged: () => void }) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const target = w.target_ml ?? 0;
  const pct = target > 0 ? Math.min(100, (w.consumed_ml / target) * 100) : 0;
  const [barRef, shownPct] = useRevealFill<HTMLDivElement>(pct);
  const met = target > 0 && w.consumed_ml >= target;
  const last = w.logs[w.logs.length - 1];

  async function run(fn: () => Promise<unknown>) {
    setBusy(true);
    setError(null);
    try {
      await fn();
      onChanged();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="water" aria-labelledby="water-heading">
      <div className="water-head">
        <h3 id="water-heading"><span className="water-icon"><WaterDrop /></span>Water</h3>
        <span className="num">
          {litres(w.consumed_ml)}{target > 0 && ` / ${litres(target)}`}
          <span className="muted">
            {target > 0 && (met ? " · goal met ✓" : ` · ${litres(target - w.consumed_ml)} to go`)}
          </span>
        </span>
      </div>
      <div className="bar water-bar" ref={barRef} role="progressbar" aria-label="Water"
           aria-valuenow={w.consumed_ml} aria-valuemax={target}>
        <div className={`bar-fill ${met ? "reached" : ""}`} style={{ width: `${shownPct}%` }} />
      </div>
      {isToday && (
        <div className="water-actions">
          <button onClick={() => { haptic("tap"); run(() => api.addWater(250)); }} disabled={busy}>+ 250 ml</button>
          <button onClick={() => { haptic("tap"); run(() => api.addWater(500)); }} disabled={busy}>+ 500 ml</button>
          <button className="ghost" onClick={() => last && run(() => api.deleteWater(last.id))}
                  disabled={busy || !last} title={last ? `Remove the last ${last.amount_ml} ml` : undefined}>
            Undo
          </button>
          <span className="muted small">or tell the chat, e.g. "drank 1 L water"</span>
        </div>
      )}
      {!target && <p className="muted small">Add your weight under Targets &amp; weight to get a daily water goal.</p>}
      {error && <p className="error small">{error}</p>}
    </section>
  );
}

function sumItems(items: Item[]) {
  return items.reduce(
    (t, i) => ({
      calories: t.calories + i.calories, protein_g: t.protein_g + i.protein_g, fiber_g: t.fiber_g + (i.fiber_g ?? 0),
      carbs_g: t.carbs_g + i.carbs_g, fat_g: t.fat_g + i.fat_g,
    }),
    { calories: 0, protein_g: 0, fiber_g: 0, carbs_g: 0, fat_g: 0 },
  );
}

type ItemActionsProps = {
  day: string;
  item: Item;
  meal: string;
  isToday: boolean;
  onChanged: () => void;
  onAskMacBro: (text: string, date?: string) => void;
  onClose: () => void;
};

/** Inline edit panel for one logged food: move/copy via a dropdown, change quantity, and icon actions. */
function ItemActions({ day, item, meal, isToday, onChanged, onAskMacBro, onClose }: ItemActionsProps) {
  const [qty, setQty] = useState(String(item.quantity));
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const name = `${item.quantity} ${item.unit} ${item.ingredient_name}`;
  const today = new Date();
  const todayIso = `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, "0")}-${String(today.getDate()).padStart(2, "0")}`;

  async function run(fn: () => Promise<unknown>) {
    setBusy(true);
    setError(null);
    try {
      await fn();
      onClose();
      onChanged();
    } catch (e) {
      setError((e as Error).message);
      setBusy(false);
    }
  }

  const [mode, setMode] = useState<"move" | "copy">("move");
  const targets = mode === "move" ? MEAL_ORDER.filter((m) => m !== meal) : MEAL_ORDER;
  const [dest, setDest] = useState<string>(targets[0]);
  const destValid = targets.includes(dest) ? dest : targets[0];
  const qtyChanged = Number(qty) > 0 && Number(qty) !== item.quantity;
  const id = item.id!;

  // Live preview of the new amount: nutrients scale with it (as the server does on save).
  const factor = Number(qty) > 0 ? Number(qty) / item.quantity : 1;

  return (
    <div className="item-actions" role="group" aria-label={`Actions for ${item.ingredient_name}`}>
      {/* 1. Change the amount in this meal: its own Save, so it's never confused with Move. */}
      <form className="ia-section ia-amount" onSubmit={(e) => { e.preventDefault(); if (qtyChanged) run(() => api.setItemQuantity(id, Number(qty))); }}>
        <label className="ia-label" htmlFor={`qty-${id}`}>Amount in {MEAL_LABEL[meal] ?? meal}</label>
        <div className="ia-row">
          <input id={`qty-${id}`} type="number" step="any" min="0.01" value={qty} onChange={(e) => setQty(e.target.value)}
                 className="ia-qty" />
          <span className="muted small">{item.unit}</span>
          <span className={`ia-preview small${qtyChanged ? " changed" : ""}`} aria-live="polite">
            <b className="num">{Math.round(item.calories * factor)}</b> kcal · <b className="num">{grams(item.protein_g * factor)}</b> protein
          </span>
          <button className="primary ia-save" disabled={busy || !qtyChanged}>Save</button>
        </div>
      </form>

      {/* 2. Move or copy the food to another meal. */}
      <form className="ia-section" onSubmit={(e) => {
        e.preventDefault();
        run(() => api.transferItem(id, destValid, mode, mode === "copy" && !isToday ? todayIso : undefined));
      }}>
        <span className="ia-label" id={`transfer-${id}`}>Move or copy to another meal</span>
        <div className="ia-row" role="group" aria-labelledby={`transfer-${id}`}>
          <div className="segmented ia-mode" role="radiogroup" aria-label="Move or copy">
            {(["move", "copy"] as const).map((m) => (
              <button key={m} type="button" role="radio" aria-checked={mode === m} className={mode === m ? "on" : ""}
                      onClick={() => setMode(m)}>{m === "move" ? "Move" : "Copy"}</button>
            ))}
          </div>
          <label className="sr-only" htmlFor={`dest-${id}`}>{mode === "move" ? "Move to" : "Copy to"}</label>
          <select id={`dest-${id}`} className="ia-select" value={destValid} onChange={(e) => setDest(e.target.value)}>
            {targets.map((m) => <option key={m} value={m}>{mode === "copy" && !isToday ? `Today's ${MEAL_LABEL[m].toLowerCase()}` : MEAL_LABEL[m]}</option>)}
          </select>
          <button className="ia-go" disabled={busy} title={`${mode === "move" ? "Move" : "Copy"} to ${MEAL_LABEL[destValid]}`}>
            {mode === "move" ? "Move" : "Copy"} <ArrowRightIcon />
          </button>
        </div>
      </form>

      <div className="ia-row ia-bottom">
        <div className="ia-icons">
          <button type="button" className="ghost icon-btn" disabled={busy} aria-label="Edit in chat" title="Edit in chat"
                  onClick={() => { onClose(); onAskMacBro(`Edit the ${item.ingredient_name} in my ${MEAL_LABEL[meal].toLowerCase()}: `, day); }}>
            <ChatIcon />
          </button>
          <button type="button" className="ghost icon-btn danger" disabled={busy} aria-label="Delete" title="Delete"
                  onClick={() => window.confirm(`Delete ${name} from ${MEAL_LABEL[meal]}?`) && run(() => api.deleteItem(id))}>
            <TrashIcon />
          </button>
          <button type="button" className="ghost icon-btn" onClick={onClose} aria-label="Close" title="Close">
            <CloseIcon />
          </button>
        </div>
      </div>
      {error && <p className="error small">{error}</p>}
    </div>
  );
}

const UNIT_SUGGESTIONS = ["g", "ml", "piece", "serving", "cup", "bowl", "slice", "tbsp", "tsp", "glass"];

/** Add a food to a meal without the chat. A saved food (from Saved Food) is added at once with its
 *  saved numbers; any other food gets an AI estimate that is only saved after "Add it". */
function AddFoodPanel({ day, meal, onChanged, onAskMacBro, onClose }: {
  day: string; meal: string; onChanged: () => void; onAskMacBro: (text: string, date?: string) => void; onClose: () => void;
}) {
  const [foods, setFoods] = useState<Food[]>([]);
  const [name, setName] = useState("");
  const [qty, setQty] = useState("");
  const [unit, setUnit] = useState("g");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [estimate, setEstimate] = useState<{ action: Action; note: string } | null>(null);
  const [noEstimate, setNoEstimate] = useState<string | null>(null);
  const [suggest, setSuggest] = useState<{ id: number; name: string; units: string[] } | null>(null);
  const [askState, setAskState] = useState<string | null>(null);
  const [estimateSource, setEstimateSource] = useState<"ai" | "general">("ai");

  useEffect(() => { api.foods().then(setFoods).catch(() => setFoods([])); }, []);

  const saved = foods.find((f) => f.name.toLowerCase() === name.trim().toLowerCase());
  const unitValid = saved ? (saved.units.includes(unit) ? unit : saved.units[0]) : unit;
  const described = `${qty} ${unitValid} ${name.trim()}`;
  const ready = name.trim() !== "" && Number(qty) > 0 && unitValid.trim() !== "";
  const mealLabel = MEAL_LABEL[meal].toLowerCase();

  /** `pick`: the saved food chosen from "Did you mean …?"; `asTyped`: the user said no to it;
   *  `typed`: the name to send instead of the box (e.g. "chicken breast, cooked" after Raw/Cooked). */
  async function send(pick?: { id: number; name: string }, asTyped = false, typed?: string) {
    setBusy(true);
    setError(null);
    setNoEstimate(null);
    setSuggest(null);
    setAskState(null);
    try {
      const r = await api.addFood({ name: pick?.name ?? typed ?? name.trim(), quantity: Number(qty),
                                    unit: unitValid.trim(),
                                    meal_type: meal, day, food_id: pick?.id ?? saved?.id ?? null, as_typed: asTyped });
      if (r.status === "added") { onClose(); onChanged(); return; }
      if (r.status === "suggest") setSuggest(r.food);
      else if (r.status === "ask_state") setAskState(r.name);
      else if (r.status === "estimate") { setEstimate({ action: r.action, note: r.note }); setEstimateSource(r.source); }
      else setNoEstimate(r.message);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  function submit(e: React.FormEvent) {
    e.preventDefault();
    if (ready) void send();
  }

  async function confirm() {
    if (!estimate) return;
    setBusy(true);
    setError(null);
    try {
      await api.confirm(estimate.action.id);
      onClose();
      onChanged();
    } catch (err) {
      setError((err as Error).message);
      setBusy(false);
    }
  }

  /** Drop the estimate (nothing is saved); `close` also closes the panel. */
  function discard(close: boolean) {
    if (estimate) void api.reject(estimate.action.id).catch(() => undefined);
    setEstimate(null);
    if (close) onClose();
  }

  if (estimate) {
    const p = estimate.action.payload;
    return (
      <div className="add-food" role="group" aria-label={`Add to ${mealLabel}`}>
        <div className="add-preview-head">
          <b>{estimateSource === "general" ? "General food list" : "AI estimate"}</b><span className="badge pending">Not saved yet</span>
        </div>
        <ul className="add-preview-items">
          {(p.items ?? []).map((it, i) => (
            <li key={i}>
              <span>{it.ingredient_name}{it.brand_name && <span className="muted"> · {it.brand_name}</span>}</span>
              <span className="muted">{it.quantity} {it.unit}</span>
            </li>
          ))}
        </ul>
        {p.totals && <MacroChips n={p.totals} />}
        {estimate.note && <p className="small add-note">{estimate.note}</p>}
        <p className="muted small">Adding it also saves the food to Saved Food, so next time it's instant.</p>
        <div className="proposal-actions">
          <button className="primary" onClick={confirm} disabled={busy}>Add it</button>
          <button onClick={() => discard(false)} disabled={busy}>Change</button>
          <button className="ghost" onClick={() => discard(true)} disabled={busy}>Cancel</button>
        </div>
        {error && <p className="error small">{error}</p>}
      </div>
    );
  }

  const listId = `saved-foods-${meal}`;
  return (
    <form className="add-food" onSubmit={submit} aria-label={`Add to ${mealLabel}`}>
      <div className="add-food-row">
        <label className="sr-only" htmlFor={`add-name-${meal}`}>Food</label>
        <input id={`add-name-${meal}`} className="add-name" list={listId} value={name} autoFocus autoComplete="off"
               placeholder="Food, e.g. paneer" onChange={(e) => { setName(e.target.value); setSuggest(null); setAskState(null); }} maxLength={200} />
        <datalist id={listId}>
          {foods.map((f) => (
            <option key={f.id} value={f.name}>{`${Math.round(f.calories)} kcal per ${f.ref_qty} ${f.ref_unit}${f.brand_name ? ` · ${f.brand_name}` : ""}`}</option>
          ))}
        </datalist>
        <label className="sr-only" htmlFor={`add-qty-${meal}`}>Quantity</label>
        <input id={`add-qty-${meal}`} className="ia-qty" type="number" step="any" min="0.01" placeholder="Qty"
               value={qty} onChange={(e) => setQty(e.target.value)} />
        <label className="sr-only" htmlFor={`add-unit-${meal}`}>Unit</label>
        {saved ? (
          <select id={`add-unit-${meal}`} className="add-unit" value={unitValid} onChange={(e) => setUnit(e.target.value)}>
            {saved.units.map((u) => <option key={u} value={u}>{u}</option>)}
          </select>
        ) : (
          <>
            <input id={`add-unit-${meal}`} className="add-unit" list={`units-${meal}`} value={unit}
                   onChange={(e) => setUnit(e.target.value)} maxLength={32} />
            <datalist id={`units-${meal}`}>{UNIT_SUGGESTIONS.map((u) => <option key={u} value={u} aria-label={u} />)}</datalist>
          </>
        )}
        <button className="primary add-go" disabled={busy || !ready}>{busy ? "Estimating…" : "Add"}</button>
        <button type="button" className="ghost icon-btn" onClick={onClose} aria-label="Close" title="Close"><CloseIcon /></button>
      </div>
      <p className="muted small add-hint">
        {!name.trim() ? "Pick one of your saved foods or type any food."
          : saved ? `Saved food: added straight away with your numbers (${saved.measures}).`
          : "New food: taken from the general food list when it's there, else the AI estimates it. You check it before it's added."}
      </p>
      {askState && (
        <div className="small add-suggest" role="status">
          <p>Was the <b>{askState}</b> weighed raw or cooked? The calories per 100 g are very different, so I'd rather ask than guess.</p>
          <div className="proposal-actions">
            {(["raw", "cooked"] as const).map((s) => (
              <button key={s} type="button" disabled={busy} onClick={() => { const n = `${askState}, ${s}`; setName(n); void send(undefined, false, n); }}>
                {s === "raw" ? "Raw" : "Cooked"}
              </button>
            ))}
          </div>
        </div>
      )}
      {suggest && (
        <div className="small add-suggest" role="status">
          <p>Did you mean <b>{suggest.name}</b>, from your saved foods?</p>
          <div className="proposal-actions">
            <button type="button" className="primary" disabled={busy} onClick={() => {
              setName(suggest.name);
              // Add at once if the typed unit fits; otherwise the unit list appears to pick from.
              if (suggest.units.includes(unitValid)) void send(suggest); else setSuggest(null);
            }}>
              Use {suggest.name}
            </button>
            <button type="button" disabled={busy} onClick={() => void send(undefined, true)}>No, add "{name.trim()}"</button>
          </div>
        </div>
      )}
      {noEstimate && (
        <p className="small">
          {noEstimate}{" "}
          <button type="button" className="link" onClick={() => { onClose(); onAskMacBro(`${described} for ${mealLabel}`, day); }}>
            Ask in chat instead
          </button>
        </p>
      )}
      {error && <p className="error small">{error}</p>}
    </form>
  );
}

const MEAL_ICON: Record<string, () => React.JSX.Element> = {
  breakfast: SunriseIcon, morning_snack: AppleIcon, lunch: BowlIcon, evening_snack: CupIcon, dinner: MoonIcon, snack: AppleIcon,
};

/** One meal as its own card, folded by default: the header (coloured icon badge, each meal has a
 *  hue in styles.css "meal cards"; calories and share of the day) and the macro chips. Unfolded:
 *  each food on its own line (pencil to edit) and + Add food. */
function MealSection({ day, meal, entries, isToday, dayTarget, onChanged, onAskMacBro }: {
  day: string; meal: string; entries: Entry[]; isToday: boolean; dayTarget: number | null;
  onChanged: () => void; onAskMacBro: (text: string, date?: string) => void;
}) {
  const [menuFor, setMenuFor] = useState<number | null>(null);
  const [adding, setAdding] = useState(false);
  const items = entries.flatMap((e) => e.items);
  const t = sumItems(items);
  const [open, setOpen] = useState(false);
  const Icon = MEAL_ICON[meal] ?? BowlIcon;
  const share = dayTarget ? Math.round((t.calories / dayTarget) * 100) : null;
  const label = MEAL_LABEL[meal] ?? meal;
  return (
    <article className={`meal-card meal-${meal}${items.length ? "" : " empty"}${open ? " open" : ""}`} aria-label={label}>
      <button type="button" className="meal-head meal-toggle" onClick={() => { setOpen(!open); if (open) { setAdding(false); setMenuFor(null); } }}
              aria-expanded={open} title={open ? "Fold" : items.length ? "Show foods, edit or add" : "Add food"}>
        <span className="meal-badge" aria-hidden="true"><Icon /></span>
        <span className="meal-title">
          <span className="meal-name">{label}</span>
          <span className="muted small">
            {items.length
              ? `${items.length} item${items.length === 1 ? "" : "s"}${share != null ? ` · ${share}% of your day` : ""}`
              : "Nothing logged yet"}
          </span>
        </span>
        {items.length > 0 && (
          <span className="meal-kcal num"><b>{Math.round(t.calories).toLocaleString()}</b><span className="muted"> kcal</span></span>
        )}
        <span className={`chevron ${open ? "open" : ""}`} aria-hidden="true"><ChevronDownIcon /></span>
      </button>
      {items.length > 0 && share != null && (
        <div className="meal-share" aria-hidden="true"><i style={{ width: `${Math.min(100, share)}%` }} /></div>
      )}
      {items.length > 0 && (
        <>
          <div className="meal-macros">
            <span className="macro-chip protein"><i />P {grams(t.protein_g)}</span>
            <span className="macro-chip fiber"><i />Fiber {grams(t.fiber_g)}</span>
            <span className="macro-chip carbs"><i />C {grams(t.carbs_g)}</span>
            <span className="macro-chip fat"><i />F {grams(t.fat_g)}</span>
          </div>
          {open && <ul className="meal-items">
            {items.map((it, idx) => (
              <li key={it.id ?? idx} className={menuFor === it.id ? "open" : ""}>
                <span className="meal-item-name">
                  {it.ingredient_name}
                  {it.brand_name && <span className="muted"> · {it.brand_name}</span>}
                </span>
                <span className="muted meal-item-qty">{it.quantity} {it.unit}</span>
                <span className="num">{Math.round(it.calories)}</span>
                {it.id != null && (
                  <button type="button" className="ghost item-menu-btn" aria-expanded={menuFor === it.id}
                          aria-label={`Edit ${it.ingredient_name}`} title="Edit"
                          onClick={() => setMenuFor(menuFor === it.id ? null : it.id!)}><PencilIcon /></button>
                )}
                {menuFor === it.id && (
                  <ItemActions day={day} item={it} meal={meal} isToday={isToday} onChanged={onChanged}
                               onAskMacBro={onAskMacBro} onClose={() => setMenuFor(null)} />
                )}
              </li>
            ))}
          </ul>}
        </>
      )}
      {open && (adding ? (
        <AddFoodPanel day={day} meal={meal} onChanged={onChanged} onAskMacBro={onAskMacBro} onClose={() => setAdding(false)} />
      ) : (
        <button type="button" className="meal-add-btn" onClick={() => { setMenuFor(null); setAdding(true); }}>
          + Add food
        </button>
      ))}
    </article>
  );
}

type DashboardProps = {
  dataVersion: number; onDataChanged: () => void; onAskMacBro: (text: string, date?: string) => void;
  /** Bumped to open "Check your progress" (an old #analysis link, the guide). */
  showProgress?: number;
};

export default function Dashboard({ dataVersion, onDataChanged, onAskMacBro, showProgress = 0 }: DashboardProps) {
  // "Check your progress": the trends (Analysis was its own tab until 2026-09-30) load only when opened.
  const [progressOpen, setProgressOpen] = useState(showProgress > 0);
  const [seenProgress, setSeenProgress] = useState(showProgress);
  if (showProgress !== seenProgress) {
    setSeenProgress(showProgress);
    setProgressOpen(true);
  }
  const [day, setDay] = useState<string | undefined>(undefined);
  const [today, setToday] = useState<string | null>(null);
  const [data, setData] = useState<DailySummary | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.daily(day)
      .then((d) => {
        setData(d);
        if (!day) setToday(d.date);
        setError(null);
      })
      .catch((e) => setError(e.message));
  }, [day, dataVersion]);

  if (error) return <section className="dashboard card error">{error}</section>;
  if (!data || !today) return <section className="dashboard card muted">Loading…</section>;

  const t = data.targets;
  const c = data.consumed;
  const byMeal: Record<string, Entry[]> = {};
  for (const e of data.entries) (byMeal[e.meal_type] ??= []).push(e);

  return (
    <div className="dashboard">
      {/* One compact tile for the day (Home has the big ring), then a card per meal. */}
      <section className="card day-summary" aria-label="Day summary">
        <div className="day-nav">
          <button className="ghost" onClick={() => setDay(shiftDay(data.date, -1))} aria-label="Previous day">‹</button>
          <span className="day-label">{friendlyDate(data.date, today)}</span>
          <button className="ghost" onClick={() => setDay(shiftDay(data.date, 1))} disabled={data.date >= today} aria-label="Next day">›</button>
        </div>
        {t ? (
          <div className="stat-strip">
            <Stat label="Calories" value={c.calories} target={t.calories} unit="kcal" tone="kcal" />
            <Stat label="Protein" value={c.protein_g} target={t.protein_g} unit="g" tone="protein" />
            <Stat label="Fiber" value={c.fiber_g} target={t.fiber_g} unit="g" tone="fiber" />
            <Stat label="Carbs" value={c.carbs_g} target={t.carbs_g} unit="g" tone="carbs" />
            <Stat label="Fat" value={c.fat_g} target={t.fat_g} unit="g" tone="fat" />
          </div>
        ) : (
          <p className="muted">No targets set.</p>
        )}
        {data.water && <Water w={data.water} isToday={data.date === today} onChanged={onDataChanged} />}
        {data.micronutrients && <Micronutrients m={data.micronutrients} />}
      </section>

      <div className="meals-head">
        <h2>Meals</h2>
        <MacBroInvite label={`Log food${data.date === today ? "" : ` for ${friendlyDate(data.date, today)}`}`} size={44}
                      onClick={() => onAskMacBro("", data.date)}>
          Lazy to add meals manually? <b>Talk to me</b>, I'll do the hard work for you.
        </MacBroInvite>
      </div>
      <div className="meals">
        {[...MEAL_ORDER, ...Object.keys(byMeal).filter((m) => !MEAL_ORDER.includes(m))].map((meal) => (
          <MealSection key={meal} day={data.date} meal={meal} entries={byMeal[meal] ?? []} isToday={data.date === today}
                       dayTarget={t?.calories ?? null} onChanged={onDataChanged} onAskMacBro={onAskMacBro} />
        ))}
      </div>

      <button type="button" className={`progress-toggle${progressOpen ? " open" : ""}`} aria-expanded={progressOpen}
              aria-controls="progress-reports" onClick={() => setProgressOpen(!progressOpen)}>
        <span className="progress-icon" aria-hidden="true"><TrendIcon /></span>
        <span className="progress-text">
          <b>Check your progress</b>
          <span className="muted small">Calories, protein, macros, meals and water over 7, 14 or 30 days</span>
        </span>
        <span className={`chevron ${progressOpen ? "open" : ""}`} aria-hidden="true"><ChevronDownIcon /></span>
      </button>
      {progressOpen && <div id="progress-reports" className="progress-reports"><AnalysisPage dataVersion={dataVersion} /></div>}
      <p className="muted small health-note">Calories, nutrients and targets are estimates to help you track, not medical advice. <a href="/privacy#health" target="_blank" rel="noopener">More</a></p>
    </div>
  );
}
