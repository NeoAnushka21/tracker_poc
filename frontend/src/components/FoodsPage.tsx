import { useEffect, useMemo, useState, type FormEvent } from "react";
import { api } from "../api";
import type { Food, MicroField } from "../types";
import { grams } from "../format";
import { PencilIcon, TrashIcon } from "./icons";

type Filter = "all" | "food" | "recipe";

const SOURCE_LABEL: Record<Food["source"], string> = {
  estimate: "learned from your logs",
  user: "edited by you",
  recipe: "your recipe",
};

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
      <p className="muted small food-source">All values {food.measures} · {SOURCE_LABEL[food.source]}</p>
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
      {isRecipe && <p className="muted small">A recipe's numbers come from its ingredients. To change them, tell the chat, e.g. "update my {food.name} recipe: 10 ml oil instead of 5".</p>}
      {error && <p className="error">{error}</p>}
      <div className="food-edit-actions">
        <button className="primary" disabled={busy}>{busy ? "Saving…" : "Save"}</button>
        <button type="button" className="ghost" onClick={onCancel}>Cancel</button>
      </div>
    </form>
  );
}

function FoodRow({ food, fields, onChanged, onDeleted }: {
  food: Food; fields: MicroField[]; onChanged: (f: Food) => void; onDeleted: (id: number) => void;
}) {
  const [editing, setEditing] = useState(false);
  const [open, setOpen] = useState(false);
  const [error, setError] = useState<string | null>(null);

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
        </div>
        <div className="food-kcal">
          <b className="num">{Math.round(food.calories).toLocaleString()}</b> kcal
          <span className="muted"> {food.measures}</span>
        </div>
        <div className="food-actions">
          <button className="ghost info-btn" onClick={() => setOpen(!open)} aria-expanded={open} aria-controls={infoId}
                  title={open ? "Hide additional info" : "Additional info"}>
            <span className="info-label">Additional info</span>
            <i className="chevron" aria-hidden="true" />
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
      {open && <FoodInfo food={food} fields={fields} id={infoId} />}
      {error && <p className="error small food-error">{error}</p>}
      {editing && (
        <EditForm food={food} fields={fields} onCancel={() => setEditing(false)} onSaved={(f) => { onChanged(f); setEditing(false); }} />
      )}
    </li>
  );
}

export default function FoodsPage({ dataVersion }: { dataVersion: number }) {
  const [foods, setFoods] = useState<Food[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [query, setQuery] = useState("");
  const [filter, setFilter] = useState<Filter>("all");
  const [microFields, setMicroFields] = useState<MicroField[]>([]);

  useEffect(() => {
    api.micronutrientFields().then(setMicroFields).catch(() => setMicroFields([]));
  }, []);

  useEffect(() => {
    api.foods().then((f) => { setFoods(f); setError(null); }).catch((e) => setError(e.message));
  }, [dataVersion]);

  const shown = useMemo(() => {
    const q = query.trim().toLowerCase();
    return (foods ?? []).filter((f) =>
      (filter === "all" || f.kind === filter) &&
      (!q || f.name.toLowerCase().includes(q) || (f.brand_name ?? "").toLowerCase().includes(q)),
    );
  }, [foods, query, filter]);

  const recipeCount = foods?.filter((f) => f.kind === "recipe").length ?? 0;

  return (
    <section className="foods card">
      <div className="foods-head">
        <div>
          <h2>Saved Food</h2>
          <p className="muted small">
            Foods are saved automatically when you confirm a meal, so next time the app reuses the same
            numbers. Save a recipe by telling the chat, e.g. "save my chapati as a recipe".
          </p>
        </div>
      </div>

      <div className="foods-tools">
        <input type="search" placeholder="Search foods" value={query} onChange={(e) => setQuery(e.target.value)} aria-label="Search foods" />
        <div className="segmented" role="radiogroup" aria-label="Show">
          {(["all", "food", "recipe"] as const).map((f) => (
            <button key={f} type="button" className={filter === f ? "on" : ""} onClick={() => setFilter(f)} aria-pressed={filter === f}>
              {f === "all" ? `All (${foods?.length ?? 0})` : f === "food" ? "Foods" : `Recipes (${recipeCount})`}
            </button>
          ))}
        </div>
      </div>

      {error && <p className="error">{error}</p>}
      {foods === null && !error && <p className="muted">Loading…</p>}
      {foods?.length === 0 && (
        <p className="muted empty-foods">Nothing saved yet. Log a meal in the chat and confirm it, and its foods will show up here.</p>
      )}
      {foods && foods.length > 0 && shown.length === 0 && <p className="muted">No matches.</p>}

      <ul className="food-list">
        {shown.map((f) => (
          <FoodRow
            key={f.id}
            food={f}
            fields={microFields}
            onChanged={(nf) => setFoods((fs) => fs?.map((x) => (x.id === nf.id ? nf : x)) ?? null)}
            onDeleted={(id) => setFoods((fs) => fs?.filter((x) => x.id !== id) ?? null)}
          />
        ))}
      </ul>
    </section>
  );
}
