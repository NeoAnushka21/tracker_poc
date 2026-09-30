import { useMemo, useState, type FormEvent } from "react";
import { api } from "../api";
import type { Food, Label, MicroField, RecipePreview } from "../types";
import { grams } from "../format";
import LabelSearch from "./LabelSearch";

export type AddKind = "brand" | "generic" | "recipe";

const CHOICES: { kind: AddKind; title: string; text: string }[] = [
  { kind: "brand", title: "Branded product", text: "A packaged food with a nutrition label. Find it on Open Food Facts or copy the label." },
  { kind: "generic", title: "Generic food", text: "A loose or home food (fruit, paneer, sabzi…) with your own numbers." },
  { kind: "recipe", title: "Recipe", text: "A dish you make: its ingredients and what the batch makes." },
];

const num = (s: string) => (s.trim() === "" ? null : Number(s));
const round1 = (n: number) => Math.round(n * 10) / 10;

/** Protein, carbs and fat at 4/4/9 kcal per gram vs the calories typed. Labels round, so only
 *  a clear gap is flagged; it never blocks saving. */
function energyGap(kcal: number | null, p: number | null, c: number | null, f: number | null): number | null {
  if (!kcal || p == null || c == null || f == null) return null;
  const est = 4 * p + 4 * c + 9 * f;
  return Math.abs(kcal - est) > Math.max(0.15 * kcal, 20) ? Math.round(est) : null;
}

type Values = {
  name: string; brand_name: string; ref_qty: string; ref_unit: string;
  calories: string; protein_g: string; carbs_g: string; fat_g: string; fiber_g: string;
  grams_per_piece: string; grams_per_serving: string;
};

const EMPTY: Values = {
  name: "", brand_name: "", ref_qty: "100", ref_unit: "g", calories: "", protein_g: "", carbs_g: "", fat_g: "",
  fiber_g: "", grams_per_piece: "", grams_per_serving: "",
};

/** Branded product and Generic food: the same fields, laid out for a pack label or for your own numbers. */
function FoodTemplate({ branded, fields, onAdded }: { branded: boolean; fields: MicroField[]; onAdded: (f: Food) => void }) {
  const [v, setV] = useState<Values>(EMPTY);
  const [micros, setMicros] = useState<Record<string, string>>({});
  const [label, setLabel] = useState<Label | null>(null);        // picked on Open Food Facts, until a number is changed
  const [finding, setFinding] = useState(false);
  const [fromLabel, setFromLabel] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const setText = (k: "name" | "brand_name") => (e: { target: { value: string } }) => setV({ ...v, [k]: e.target.value });
  // Changing a number after picking a label means the typed numbers are what gets saved.
  const setNum = (k: keyof Values) => (e: { target: { value: string } }) => { setV({ ...v, [k]: e.target.value }); setLabel(null); };
  const setMicro = (key: string, value: string) => { setMicros({ ...micros, [key]: value }); setLabel(null); };

  function pick(l: Label) {
    setV({
      ...v,
      name: v.name.trim() || l.name,
      brand_name: v.brand_name.trim() || (l.brand ?? ""),
      ref_qty: String(l.ref_qty), ref_unit: l.ref_unit,
      calories: String(l.calories), protein_g: String(l.protein_g), carbs_g: String(l.carbs_g), fat_g: String(l.fat_g),
      fiber_g: String(l.fiber_g), grams_per_serving: l.grams_per_serving ? String(l.grams_per_serving) : v.grams_per_serving,
    });
    setMicros(Object.fromEntries(Object.entries(l.micronutrients ?? {}).map(([k, n]) => [k, String(n)])));
    setLabel(l);
    setFromLabel(true);
    setFinding(false);
  }

  const gap = energyGap(num(v.calories), num(v.protein_g), num(v.carbs_g), num(v.fat_g));
  const sodium = fields.find((f) => f.key === "sodium_mg");
  const moreFields = branded ? fields.filter((f) => f.key !== "sodium_mg") : fields;

  async function submit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      onAdded(await api.createFood({
        name: v.name.trim(),
        brand_name: branded ? v.brand_name.trim() || null : null,
        ref_qty: Number(v.ref_qty), ref_unit: v.ref_unit.trim(),
        calories: Number(v.calories), protein_g: Number(v.protein_g), carbs_g: Number(v.carbs_g), fat_g: Number(v.fat_g),
        fiber_g: num(v.fiber_g) ?? 0,
        grams_per_piece: num(v.grams_per_piece), grams_per_serving: num(v.grams_per_serving),
        micronutrients: Object.fromEntries(
          Object.entries(micros).filter(([, s]) => s.trim() !== "").map(([k, s]) => [k, Number(s)])),
        label_checked: branded && fromLabel,
        correct_logs: false,
        label_code: label?.code ?? null,
      }));
    } catch (err) {
      setError((err as Error).message);
      setBusy(false);
    }
  }

  const input = (k: keyof Values, text: string, opts: { required?: boolean; placeholder?: string } = {}) => (
    <label>{text}<input type="number" step="any" min="0" value={v[k]} onChange={setNum(k)} required={opts.required} placeholder={opts.placeholder} /></label>
  );

  return (
    <form className="food-edit add-template" onSubmit={submit}>
      {branded ? (
        <>
          <div className="food-edit-grid">
            <label className="wide">Brand<input value={v.brand_name} onChange={setText("brand_name")} required maxLength={200} placeholder="e.g. Amul" /></label>
            <label className="wide">Product<input value={v.name} onChange={setText("name")} required maxLength={200} placeholder="e.g. butter" /></label>
          </div>
          <h4>1. Find the label <span className="muted">(optional)</span></h4>
          {label && (
            <p className="small label-picked">
              From Open Food Facts: <b>{label.name}</b>{label.brand ? ` · ${label.brand}` : ""} (barcode {label.code}).
              Change any number below and your typed values are saved instead.
            </p>
          )}
          {finding ? (
            <LabelSearch initialQuery={`${v.brand_name} ${v.name}`.trim()} onPick={pick} />
          ) : (
            <button type="button" className="ghost" onClick={() => setFinding(true)}>
              {label ? "Pick another product" : "Search Open Food Facts"}
            </button>
          )}
          <h4>2. Nutrition table <span className="muted">(as printed on the pack)</span></h4>
          <div className="food-edit-grid">
            <label>Per<input type="number" step="any" min="0.01" value={v.ref_qty} onChange={setNum("ref_qty")} required /></label>
            <label>Unit
              <select value={v.ref_unit} onChange={setNum("ref_unit")}>
                <option value="g">g</option><option value="ml">ml</option>
              </select>
            </label>
            {input("calories", "Energy (kcal)", { required: true })}
            {input("protein_g", "Protein (g)", { required: true })}
            {input("carbs_g", "Carbohydrate (g)", { required: true })}
            {input("fiber_g", "of which fibre (g)", { placeholder: "optional" })}
            {input("fat_g", "Total fat (g)", { required: true })}
            {sodium && (
              <label>Sodium (mg)<input type="number" step="any" min="0" placeholder="optional" value={micros.sodium_mg ?? ""}
                                       onChange={(e) => setMicro("sodium_mg", e.target.value)} /></label>
            )}
            {input("grams_per_serving", "Serving size (g)", { placeholder: "optional" })}
            {input("grams_per_piece", "g per piece", { placeholder: "e.g. 1 biscuit" })}
          </div>
        </>
      ) : (
        <>
          <p className="muted small">
            Common foods (banana, rice, ghee, dals…) are already on the general food list, so you only need this for
            foods that aren't, or to use your own numbers.
          </p>
          <div className="food-edit-grid">
            <label className="wide">Name<input value={v.name} onChange={setText("name")} required maxLength={200} placeholder="e.g. paneer" /></label>
            <label>Per<input type="number" step="any" min="0.01" value={v.ref_qty} onChange={setNum("ref_qty")} required /></label>
            <label>Unit
              <select value={v.ref_unit} onChange={setNum("ref_unit")}>
                <option value="g">g</option><option value="ml">ml</option>
                <option value="piece">piece</option><option value="serving">serving</option>
              </select>
            </label>
            {input("calories", "kcal", { required: true })}
            {input("protein_g", "Protein (g)", { required: true })}
            {input("carbs_g", "Carbs (g)", { required: true })}
            {input("fat_g", "Fat (g)", { required: true })}
            {input("fiber_g", "Fiber (g)", { placeholder: "optional" })}
            {input("grams_per_piece", "g per piece", { placeholder: "optional" })}
            {input("grams_per_serving", "g per serving", { placeholder: "optional" })}
          </div>
        </>
      )}
      {moreFields.length > 0 && (
        <details className="food-micros-edit">
          <summary>{branded ? "More nutrients from the label" : "Additional nutrients"} <span className="muted">(optional, per {v.ref_qty || "?"} {v.ref_unit}; blank = unknown)</span></summary>
          <div className="food-edit-grid">
            {moreFields.map((f) => (
              <label key={f.key}>
                {f.label} ({f.unit}{f.kind === "limit" ? ", limit" : ""})
                <input type="number" step="any" min="0" placeholder="–" value={micros[f.key] ?? ""} onChange={(e) => setMicro(f.key, e.target.value)} />
              </label>
            ))}
          </div>
        </details>
      )}
      {gap != null && (
        <p className="small energy-warning" role="status">
          Protein, carbs and fat add up to about {gap} kcal, but {v.calories} kcal is entered. Worth a second look
          (labels round a little, so small gaps are fine).
        </p>
      )}
      {branded && (
        <label className="check">
          <input type="checkbox" checked={fromLabel} onChange={(e) => setFromLabel(e.target.checked)} />
          These values are from the pack label
        </label>
      )}
      {error && <p className="error">{error}</p>}
      <div className="food-edit-actions">
        <button className="primary" disabled={busy}>{busy ? "Saving…" : "Add to Saved Food"}</button>
      </div>
    </form>
  );
}

type Row = { name: string; quantity: string; unit: string };
const NEW_ROW: Row = { name: "", quantity: "", unit: "g" };
const COMMON_UNITS = ["g", "ml", "piece", "serving", "tbsp", "tsp", "cup"];

/** "Paneer · Amul" for branded foods, so two foods with one name can both be picked. */
const pickName = (f: Food) => (f.brand_name ? `${f.name} · ${f.brand_name}` : f.name);

function RecipeTemplate({ foods, onAdded }: { foods: Food[]; onAdded: (f: Food) => void }) {
  const [name, setName] = useState("");
  const [rows, setRows] = useState<Row[]>([{ ...NEW_ROW }, { ...NEW_ROW }]);
  const [count, setCount] = useState("");
  const [countUnit, setCountUnit] = useState<"servings" | "pieces">("servings");
  const [cooked, setCooked] = useState("");
  const [preview, setPreview] = useState<RecipePreview | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState<"calc" | "save" | null>(null);

  const byName = useMemo(() => new Map(foods.map((f) => [pickName(f).toLowerCase(), f])), [foods]);

  const changed = () => { setPreview(null); setError(null); };
  const setRow = (i: number, k: keyof Row, value: string) => { setRows(rows.map((r, j) => (j === i ? { ...r, [k]: value } : r))); changed(); };

  function body() {
    const used = rows.filter((r) => r.name.trim() || r.quantity.trim());
    return {
      name: name.trim(),
      ingredients: used.map((r) => {
        const saved = byName.get(r.name.trim().toLowerCase());
        return { name: saved ? saved.name : r.name.trim(), food_id: saved?.id ?? null, quantity: Number(r.quantity), unit: r.unit.trim() };
      }),
      yield_pieces: countUnit === "pieces" ? num(count) : null,
      yield_servings: countUnit === "servings" ? num(count) : null,
      cooked_weight_g: num(cooked),
    };
  }

  async function run(kind: "calc" | "save") {
    setBusy(kind);
    setError(null);
    try {
      if (kind === "calc") setPreview(await api.previewRecipe(body()));
      else onAdded(await api.createRecipe(body()));
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(null);
    }
  }

  const FROM: Record<string, string> = { library: "saved", recipe: "your recipe", general: "general list" };
  return (
    <form className="food-edit add-template" onSubmit={(e) => { e.preventDefault(); run("save"); }}>
      <div className="food-edit-grid">
        <label className="wide">Recipe name<input value={name} onChange={(e) => { setName(e.target.value); changed(); }} required maxLength={200} placeholder="e.g. paneer bhurji" /></label>
      </div>
      <h4>Ingredients <span className="muted">(raw, for the whole batch)</span></h4>
      <datalist id="recipe-food-names">
        {foods.map((f) => <option key={f.id} value={pickName(f)}>{pickName(f)}</option>)}
      </datalist>
      <datalist id="recipe-units">{COMMON_UNITS.map((u) => <option key={u} value={u}>{u}</option>)}</datalist>
      <ul className="recipe-rows">
        {rows.map((r, i) => (
          <li key={i}>
            <input aria-label={`Ingredient ${i + 1}`} list="recipe-food-names" placeholder="Ingredient" value={r.name}
                   onChange={(e) => setRow(i, "name", e.target.value)} maxLength={200} />
            <input aria-label={`Amount of ingredient ${i + 1}`} type="number" step="any" min="0" placeholder="Amount"
                   value={r.quantity} onChange={(e) => setRow(i, "quantity", e.target.value)} />
            <input aria-label={`Unit of ingredient ${i + 1}`} list="recipe-units" value={r.unit}
                   onChange={(e) => setRow(i, "unit", e.target.value)} maxLength={32} />
            <button type="button" className="ghost icon-btn danger" aria-label={`Remove ingredient ${i + 1}`} title="Remove"
                    disabled={rows.length === 1} onClick={() => { setRows(rows.filter((_, j) => j !== i)); changed(); }}>×</button>
          </li>
        ))}
      </ul>
      <button type="button" className="link" onClick={() => setRows([...rows, { ...NEW_ROW }])}>+ Add ingredient</button>
      <p className="muted small">
        Ingredients come from your Saved Food (suggested as you type) or the general food list. Foods from the general
        list are saved to Saved Food too. Anything else, add it first as a generic food or branded product.
      </p>
      <h4>What it makes</h4>
      <div className="food-edit-grid">
        <label>Makes<input type="number" step="any" min="0" value={count} onChange={(e) => { setCount(e.target.value); changed(); }} placeholder="e.g. 4" /></label>
        <label>&nbsp;
          <select value={countUnit} onChange={(e) => { setCountUnit(e.target.value as "servings" | "pieces"); changed(); }}>
            <option value="servings">servings</option><option value="pieces">pieces</option>
          </select>
        </label>
        <label className="wide">Cooked weight of the batch (g)
          <input type="number" step="any" min="0" value={cooked} onChange={(e) => { setCooked(e.target.value); changed(); }} placeholder="optional: lets you log it in grams" />
        </label>
      </div>
      {preview && (
        <div className="recipe-preview" role="status">
          <b className="num">{Math.round(preview.per_ref.calories)} kcal</b> per {preview.ref_qty} {preview.ref_unit}
          <span className="muted"> · P {grams(preview.per_ref.protein_g)} · C {grams(preview.per_ref.carbs_g)} · F {grams(preview.per_ref.fat_g)}</span>
          <ul className="ingredient-list">
            {preview.ingredients.map((i, k) => (
              <li key={k}>
                <span>{i.quantity} {i.unit} {i.name} <span className="source-tag">{FROM[i.from]}</span></span>
                <span className="muted num">{Math.round(i.calories)} kcal</span>
              </li>
            ))}
          </ul>
          <p className="muted small">Whole batch: {Math.round(preview.batch_totals.calories)} kcal, {round1(preview.batch_totals.protein_g)} g protein.</p>
        </div>
      )}
      {error && <p className="error">{error}</p>}
      <div className="food-edit-actions">
        <button type="button" className="ghost" disabled={busy !== null} onClick={() => run("calc")}>{busy === "calc" ? "Calculating…" : "Calculate"}</button>
        <button className="primary" disabled={busy !== null}>{busy === "save" ? "Saving…" : "Save recipe"}</button>
      </div>
    </form>
  );
}

/** Saved Food → + Add: pick what to add, then fill in its template. */
export default function AddFoodPanel({ foods, fields, onAdded, onClose }: {
  foods: Food[]; fields: MicroField[]; onAdded: (f: Food, kind: AddKind) => void; onClose: () => void;
}) {
  const [kind, setKind] = useState<AddKind | null>(null);
  const choice = CHOICES.find((c) => c.kind === kind);
  return (
    <div className="add-food-panel">
      <div className="add-food-head">
        <h3>{choice ? `Add a ${choice.title.toLowerCase()}` : "What do you want to add?"}</h3>
        <div>
          {kind && <button type="button" className="ghost" onClick={() => setKind(null)}>Change type</button>}
          <button type="button" className="ghost" onClick={onClose}>Close</button>
        </div>
      </div>
      {!kind && (
        <div className="add-choices">
          {CHOICES.map((c) => (
            <button key={c.kind} type="button" className="add-choice" onClick={() => setKind(c.kind)}>
              <b>{c.title}</b>
              <span className="muted small">{c.text}</span>
            </button>
          ))}
        </div>
      )}
      {kind === "brand" && <FoodTemplate key="brand" branded fields={fields} onAdded={(f) => onAdded(f, "brand")} />}
      {kind === "generic" && <FoodTemplate key="generic" branded={false} fields={fields} onAdded={(f) => onAdded(f, "generic")} />}
      {kind === "recipe" && <RecipeTemplate foods={foods} onAdded={(f) => onAdded(f, "recipe")} />}
    </div>
  );
}
