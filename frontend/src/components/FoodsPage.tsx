import { useEffect, useMemo, useState, type FormEvent } from "react";
import { api } from "../api";
import type { Food, MicroField } from "../types";
import LabelSearch from "./LabelSearch";
import AddFoodPanel, { type AddKind } from "./AddFoodPanel";
import { grams } from "../format";
import { ChevronDownIcon, PencilIcon, TrashIcon } from "./icons";

type Filter = "generic" | "brand" | "recipe";

const TABS: { id: Filter; label: string }[] = [
  { id: "generic", label: "Generic" },
  { id: "brand", label: "Branded" },
  { id: "recipe", label: "My Recipes" },
];

const SOURCE_LABEL: Record<Food["source"], string> = {
  estimate: "learned from your logs",
  user: "edited by you",
  recipe: "your recipe",
  general: "from the general food list (USDA)",
  label: "from the pack label",
};

function sourceText(f: Food): string {
  if (f.source === "label") {
    return f.off_code ? `from the pack label (Open Food Facts, barcode ${f.off_code})` : "from the pack label, typed in by you";
  }
  return isBranded(f) ? `${SOURCE_LABEL[f.source]} · label not checked yet` : SOURCE_LABEL[f.source];
}

const isBranded = (f: Food) => f.kind === "food" && !!f.brand_name;

/** Which tab a food lives in: recipes, branded foods, everything else is generic. */
const tabOf = (f: Food): Filter => (f.kind === "recipe" ? "recipe" : isBranded(f) ? "brand" : "generic");

/** "Amul" and "amul " are one brand. */
const brandKey = (f: Food) => (f.brand_name ?? "").trim().toLowerCase();

function yieldText(f: Food): string {
  const parts: string[] = [];
  if (f.yield_pieces) parts.push(`makes ${f.yield_pieces} pieces`);
  if (f.yield_servings) parts.push(`${f.yield_servings} servings`);
  if (f.cooked_weight_g) parts.push(`${f.cooked_weight_g} g cooked`);
  return parts.join(" · ");
}

/** 0.025 → "0.03", 47.8 → "47.8", 1387.2 → "1387": enough precision for a label. */
function microValue(v: number): string {
  return String(v >= 100 ? Math.round(v) : Math.round(v * 100) / 100);
}

const MACROS = [
  { key: "protein_g", label: "Protein", tone: "protein" },
  { key: "carbs_g", label: "Carbs", tone: "carbs" },
  { key: "fat_g", label: "Fat", tone: "fat" },
  { key: "fiber_g", label: "Fiber", tone: "fiber" },
] as const;

/** Everything behind "Additional info": macros, micronutrients, where the numbers came from,
 *  and a recipe's ingredients. All per the food's reference amount (`measures`). */
function FoodInfo({ food, fields, id }: { food: Food; fields: MicroField[]; id: string }) {
  const m = food.micronutrients ?? {};
  const known = fields.filter((f) => m[f.key] != null);
  return (
    <div className="food-info" id={id}>
      <div className="food-info-macros">
        {MACROS.map((x) => (
          <div key={x.key} className={`food-macro ${x.tone}`}>
            <span><i className="swatch" aria-hidden="true" />{x.label}</span>
            <b className="num">{grams(food[x.key])}</b>
          </div>
        ))}
      </div>
      <h4>Micronutrients <span className="muted">· {known.length} of {fields.length} known</span></h4>
      {known.length ? (
        <ul className="food-micros">
          {known.map((f) => (
            <li key={f.key}>{f.label}{f.kind === "limit" ? " (limit)" : ""} <b className="num">{microValue(m[f.key])} {f.unit}</b></li>
          ))}
        </ul>
      ) : (
        <p className="muted small">None saved yet. Add them with the pencil (Additional nutrients).</p>
      )}
      {food.kind === "recipe" && food.ingredients && food.ingredients.length > 0 && (
        <>
          <h4>Ingredients <span className="muted">· whole batch{yieldText(food) ? `, ${yieldText(food)}` : ""}</span></h4>
          <ul className="ingredient-list">
            {food.ingredients.map((i) => (
              <li key={i.food_id}>
                <span>{i.quantity} {i.unit} {i.name}</span>
                <span className="muted num">{i.calories == null ? "–" : `${Math.round(i.calories)} kcal`}</span>
              </li>
            ))}
          </ul>
        </>
      )}
      <p className="muted small food-source">All values {food.measures} · {sourceText(food)}</p>
    </div>
  );
}

function EditForm({ food, fields, onSaved, onCancel }: {
  food: Food; fields: MicroField[]; onSaved: (f: Food) => void; onCancel: () => void;
}) {
  const isRecipe = food.kind === "recipe";
  const [v, setV] = useState({
    name: food.name,
    brand_name: food.brand_name ?? "",
    ref_qty: String(food.ref_qty),
    ref_unit: food.ref_unit,
    calories: String(food.calories),
    protein_g: String(food.protein_g),
    carbs_g: String(food.carbs_g),
    fat_g: String(food.fat_g),
    fiber_g: String(food.fiber_g),
    grams_per_piece: food.grams_per_piece == null ? "" : String(food.grams_per_piece),
    grams_per_serving: food.grams_per_serving == null ? "" : String(food.grams_per_serving),
  });
  // Blank = unknown (not zero), so a missing value never pretends the food has none.
  const [micros, setMicros] = useState<Record<string, string>>(() =>
    Object.fromEntries(Object.entries(food.micronutrients ?? {}).map(([k, n]) => [k, String(n)])));
  const [labelChecked, setLabelChecked] = useState(food.label_checked);
  const [correctLogs, setCorrectLogs] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const set = (k: keyof typeof v) => (e: { target: { value: string } }) => setV({ ...v, [k]: e.target.value });
  const optNum = (s: string) => (s.trim() === "" ? null : Number(s));

  async function submit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      onSaved(await api.updateFood(food.id, {
        name: v.name.trim(),
        brand_name: v.brand_name.trim() || null,
        ref_qty: Number(v.ref_qty),
        ref_unit: v.ref_unit.trim(),
        calories: Number(v.calories),
        protein_g: Number(v.protein_g),
        carbs_g: Number(v.carbs_g),
        fat_g: Number(v.fat_g),
        fiber_g: Number(v.fiber_g),
        grams_per_piece: optNum(v.grams_per_piece),
        grams_per_serving: optNum(v.grams_per_serving),
        micronutrients: Object.fromEntries(
          Object.entries(micros).filter(([, s]) => s.trim() !== "").map(([k, s]) => [k, Number(s)])),
        label_checked: labelChecked,
        correct_logs: labelChecked && correctLogs,
      }));
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <form className="food-edit" onSubmit={submit}>
      <div className="food-edit-grid">
        <label className="wide">Name<input value={v.name} onChange={set("name")} required maxLength={200} /></label>
        {!isRecipe && (
          <>
            <label className="wide">Brand <span className="muted">(optional)</span><input value={v.brand_name} onChange={set("brand_name")} maxLength={200} /></label>
            <label>Per amount<input type="number" step="any" min="0.01" value={v.ref_qty} onChange={set("ref_qty")} required /></label>
            <label>Unit<input value={v.ref_unit} onChange={set("ref_unit")} required placeholder="g, ml, piece" /></label>
            <label>kcal<input type="number" step="any" min="0" value={v.calories} onChange={set("calories")} required /></label>
            <label>Protein (g)<input type="number" step="any" min="0" value={v.protein_g} onChange={set("protein_g")} required /></label>
            <label>Carbs (g)<input type="number" step="any" min="0" value={v.carbs_g} onChange={set("carbs_g")} required /></label>
            <label>Fat (g)<input type="number" step="any" min="0" value={v.fat_g} onChange={set("fat_g")} required /></label>
            <label>Fiber (g)<input type="number" step="any" min="0" value={v.fiber_g} onChange={set("fiber_g")} /></label>
            <label>g per piece<input type="number" step="any" min="0.01" value={v.grams_per_piece} onChange={set("grams_per_piece")} placeholder="optional" /></label>
            <label>g per serving<input type="number" step="any" min="0.01" value={v.grams_per_serving} onChange={set("grams_per_serving")} placeholder="optional" /></label>
          </>
        )}
      </div>
      {!isRecipe && fields.length > 0 && (
        <fieldset className="food-micros-edit">
          <legend>
            Additional nutrients{" "}
            <span className="muted">(optional, per {v.ref_qty || "?"} {v.ref_unit}; leave blank if unknown)</span>
          </legend>
          <div className="food-edit-grid">
            {fields.map((f) => (
              <label key={f.key}>
                {f.label} ({f.unit}{f.kind === "limit" ? ", limit" : ""})
                <input type="number" step="any" min="0" placeholder="–" value={micros[f.key] ?? ""}
                       onChange={(e) => setMicros({ ...micros, [f.key]: e.target.value })} />
              </label>
            ))}
          </div>
        </fieldset>
      )}
      {!isRecipe && v.brand_name.trim() && (
        <div className="label-ticks">
          <label className="check">
            <input type="checkbox" checked={labelChecked} onChange={(e) => setLabelChecked(e.target.checked)} />
            These values are from the pack label
          </label>
          {labelChecked && (
            <label className="check">
              <input type="checkbox" checked={correctLogs} onChange={(e) => setCorrectLogs(e.target.checked)} />
              Also correct the times I've already logged it
            </label>
          )}
        </div>
      )}
      {isRecipe && <p className="muted small">A recipe's numbers come from its ingredients. To change them, tell the chat, e.g. "update my {food.name} recipe: 10 ml oil instead of 5".</p>}
      {error && <p className="error">{error}</p>}
      <div className="food-edit-actions">
        <button className="primary" disabled={busy}>{busy ? "Saving…" : "Save"}</button>
        <button type="button" className="ghost" onClick={onCancel}>Cancel</button>
      </div>
    </form>
  );
}

/** Find the food's pack label on Open Food Facts and use it. Nothing changes until "Use this". */
function LabelCheck({ food, onApplied, onClose }: {
  food: Food; onApplied: (f: Food) => void; onClose: () => void;
}) {
  const [correctLogs, setCorrectLogs] = useState(true);
  const [busy, setBusy] = useState<string | null>(null);   // the barcode being saved
  const [error, setError] = useState<string | null>(null);

  async function applyLabel(code: string) {
    setBusy(code);
    setError(null);
    try {
      onApplied(await api.applyLabel(food.id, code, correctLogs));
    } catch (err) {
      setError((err as Error).message);
      setBusy(null);
    }
  }

  return (
    <div className="label-check">
      <p className="muted small">
        Saved now: <b className="num">{Math.round(food.calories)}</b> kcal {food.measures}. Pick the product that
        matches your pack.
      </p>
      <LabelSearch initialQuery={`${food.brand_name ?? ""} ${food.name}`.trim()} busyCode={busy} onPick={(l) => applyLabel(l.code)} />
      {error && <p className="error small">{error}</p>}
      <label className="check small">
        <input type="checkbox" checked={correctLogs} onChange={(e) => setCorrectLogs(e.target.checked)} />
        Also correct the times I've already logged it
      </label>
      <div className="label-check-foot">
        <button type="button" className="ghost" onClick={onClose}>Close</button>
      </div>
    </div>
  );
}

function FoodRow({ food, fields, onChanged, onDeleted }: {
  food: Food; fields: MicroField[]; onChanged: (f: Food) => void; onDeleted: (id: number) => void;
}) {
  const [editing, setEditing] = useState(false);
  const [open, setOpen] = useState(false);
  const [checking, setChecking] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  function saved(f: Food, how: string) {
    onChanged(f);
    const n = f.logs_corrected ?? 0;
    setNotice(n ? `${how} ${n} past log${n === 1 ? "" : "s"} corrected.` : how);
  }

  async function remove() {
    if (!window.confirm(`Delete "${food.name}" from your ${food.kind === "recipe" ? "recipes" : "foods"}? Past logs won't change.`)) return;
    setError(null);
    try {
      await api.deleteFood(food.id);
      onDeleted(food.id);
    } catch (err) {
      setError((err as Error).message);
    }
  }

  const infoId = `food-info-${food.id}`;
  return (
    <li className={`food-row ${food.kind}${open ? " open" : ""}${editing ? " editing" : ""}`}>
      <div className="food-line">
        <div className="food-title">
          <span className="food-name">{food.name}</span>
          {food.brand_name && <span className="muted"> · {food.brand_name}</span>}
          {food.kind === "recipe" && <span className="source-tag recipe">recipe</span>}
          {isBranded(food) && (food.label_checked
            ? <span className="source-tag label" title="Numbers from the pack label">label ✓</span>
            : <span className="source-tag unchecked" title="Numbers are the AI's estimate of the label">label not checked</span>)}
        </div>
        <div className="food-kcal">
          <b className="num">{Math.round(food.calories).toLocaleString()}</b> kcal
          <span className="muted"> {food.measures}</span>
        </div>
        <div className="food-actions">
          <button className="ghost info-btn" onClick={() => setOpen(!open)} aria-expanded={open} aria-controls={infoId}
                  title={open ? "Hide additional info" : "Additional info"}>
            <span className="info-label">Additional info</span>
            <span className="chevron" aria-hidden="true"><ChevronDownIcon /></span>
          </button>
          <button className={`ghost icon-btn ${editing ? "on" : ""}`} onClick={() => setEditing(!editing)}
                  aria-label={`${editing ? "Close editing" : "Edit"} ${food.name}`} title={editing ? "Close" : "Edit"} aria-pressed={editing}>
            <PencilIcon />
          </button>
          <button className="ghost icon-btn danger" onClick={remove} aria-label={`Delete ${food.name}`} title="Delete">
            <TrashIcon />
          </button>
        </div>
      </div>
      {isBranded(food) && !checking && !editing && (
        <div className="label-nudge small">
          {!food.label_checked && <span className="muted">These numbers are the AI's estimate. </span>}
          <button className="link" onClick={() => { setChecking(true); setNotice(null); }}>
            {food.label_checked ? "Check label again" : "Check label"}
          </button>
        </div>
      )}
      {checking && (
        <LabelCheck food={food} onClose={() => setChecking(false)}
                    onApplied={(f) => { saved(f, "Label saved."); setChecking(false); }} />
      )}
      {notice && <p className="small food-notice" role="status">{notice}</p>}
      {open && <FoodInfo food={food} fields={fields} id={infoId} />}
      {error && <p className="error small food-error">{error}</p>}
      {editing && (
        <EditForm food={food} fields={fields} onCancel={() => setEditing(false)}
                  onSaved={(f) => { saved(f, "Saved."); setEditing(false); }} />
      )}
    </li>
  );
}

const EMPTY_TAB: Record<Filter, string> = {
  generic: "No generic foods yet. They're saved when you confirm a meal, or add one with + Add.",
  brand: 'No branded foods yet. Name the brand when you log, e.g. "10 g Amul butter", or add one with + Add.',
  recipe: 'No recipes yet. Add one with + Add → Recipe, or tell the chat, e.g. "save my chapati as a recipe".',
};

export default function FoodsPage({ dataVersion }: { dataVersion: number }) {
  const [foods, setFoods] = useState<Food[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [query, setQuery] = useState("");
  const [filter, setFilter] = useState<Filter>("generic");
  const [microFields, setMicroFields] = useState<MicroField[]>([]);
  const [adding, setAdding] = useState(false);
  const [added, setAdded] = useState<string | null>(null);

  useEffect(() => {
    api.micronutrientFields().then(setMicroFields).catch(() => setMicroFields([]));
  }, []);

  useEffect(() => {
    api.foods().then((f) => { setFoods(f); setError(null); }).catch((e) => setError(e.message));
  }, [dataVersion]);

  const matching = useMemo(() => {
    const q = query.trim().toLowerCase();
    return (foods ?? []).filter((f) =>
      !q || f.name.toLowerCase().includes(q) || (f.brand_name ?? "").toLowerCase().includes(q));
  }, [foods, query]);

  /** Foods per tab (after the search), for the counts and the "found in" hint. */
  const counts = useMemo(() => {
    const c: Record<Filter, number> = { generic: 0, brand: 0, recipe: 0 };
    for (const f of matching) c[tabOf(f)] += 1;
    return c;
  }, [matching]);

  const shown = useMemo(() => matching.filter((f) => tabOf(f) === filter), [matching, filter]);

  /** Branded tab: one group per brand, A to Z; in each, foods whose label isn't checked come first. */
  const brandGroups = useMemo(() => {
    if (filter !== "brand") return [];
    const groups = new Map<string, Food[]>();
    for (const f of shown) groups.set(brandKey(f), [...(groups.get(brandKey(f)) ?? []), f]);
    return [...groups.values()]
      .map((fs) => [...fs].sort((a, b) => Number(a.label_checked) - Number(b.label_checked) || a.name.localeCompare(b.name)))
      .sort((a, b) => (a[0].brand_name ?? "").localeCompare(b[0].brand_name ?? ""));
  }, [shown, filter]);

  const toCheck = foods?.filter((f) => isBranded(f) && !f.label_checked).length ?? 0;

  const SHOW_AFTER_ADD: Record<AddKind, Filter> = { brand: "brand", generic: "generic", recipe: "recipe" };

  async function onAdded(f: Food, kind: AddKind) {
    setAdding(false);
    setQuery("");
    setFilter(SHOW_AFTER_ADD[kind]);
    setAdded(`Added ${f.name}${f.brand_name ? ` · ${f.brand_name}` : ""}.`);
    // Reload: a recipe can also add its general-list ingredients to Saved Food.
    try { setFoods(await api.foods()); } catch { setFoods((fs) => [f, ...(fs ?? [])]); }
  }

  const row = (f: Food) => (
    <FoodRow
      key={f.id}
      food={f}
      fields={microFields}
      onChanged={(nf) => setFoods((fs) => fs?.map((x) => (x.id === nf.id ? nf : x)) ?? null)}
      onDeleted={(id) => setFoods((fs) => fs?.filter((x) => x.id !== id) ?? null)}
    />
  );

  return (
    <section className="foods card">
      <div className="foods-head">
        <div>
          <h2>Saved Food</h2>
          <p className="muted small">
            Foods are saved automatically when you confirm a meal, so next time the app reuses the same
            numbers. Add your own with <b>+ Add</b>: a branded product, a generic food or a recipe (or tell the
            chat, e.g. "save my chapati as a recipe").
          </p>
        </div>
        {!adding && (
          <button type="button" className="primary foods-add-btn" onClick={() => { setAdding(true); setAdded(null); }}>+ Add</button>
        )}
      </div>

      {adding && (
        <AddFoodPanel foods={foods ?? []} fields={microFields} onAdded={onAdded} onClose={() => setAdding(false)} />
      )}
      {added && <p className="small food-notice" role="status">{added}</p>}

      <div className="foods-tools">
        <input type="search" placeholder="Search foods" value={query} onChange={(e) => setQuery(e.target.value)} aria-label="Search foods" />
        <div className="segmented" role="radiogroup" aria-label="Show">
          {TABS.map(({ id: f, label }) => (
            <button key={f} type="button" className={filter === f ? "on" : ""} onClick={() => setFilter(f)} aria-pressed={filter === f}>
              {label} ({counts[f]})
              {f === "brand" && toCheck > 0 && (
                <span className="to-check" title={`${toCheck} label${toCheck === 1 ? "" : "s"} not checked`}
                      aria-label={`${toCheck} not checked`}>{toCheck}</span>
              )}
            </button>
          ))}
        </div>
      </div>

      {error && <p className="error">{error}</p>}
      {foods === null && !error && <p className="muted">Loading…</p>}
      {foods?.length === 0 && (
        <p className="muted empty-foods">Nothing saved yet. Log a meal in the chat and confirm it, and its foods will show up here, or press <b>+ Add</b>.</p>
      )}
      {foods && foods.length > 0 && shown.length === 0 && (
        query.trim() ? (
          <p className="muted">
            No matches in {TABS.find((t) => t.id === filter)!.label}.
            {TABS.filter((t) => counts[t.id] > 0).map((t) => (
              <button key={t.id} type="button" className="link found-in" onClick={() => setFilter(t.id)}>
                {t.label} has {counts[t.id]}
              </button>
            ))}
          </p>
        ) : (
          <p className="muted">{EMPTY_TAB[filter]}</p>
        )
      )}

      {filter === "brand" ? (
        brandGroups.map((fs) => (
          <div key={brandKey(fs[0])} className="brand-group">
            <h3>{fs[0].brand_name} <span className="muted small">· {fs.length}</span></h3>
            <ul className="food-list">{fs.map(row)}</ul>
          </div>
        ))
      ) : (
        <ul className="food-list">{shown.map(row)}</ul>
      )}
    </section>
  );
}
