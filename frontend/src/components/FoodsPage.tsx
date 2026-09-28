import { useEffect, useMemo, useState, type FormEvent } from "react";
import { api } from "../api";
import type { Food } from "../types";
import MacroChips from "./MacroChips";
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

function EditForm({ food, onSaved, onCancel }: { food: Food; onSaved: (f: Food) => void; onCancel: () => void }) {
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
      {isRecipe && <p className="muted small">A recipe's numbers come from its ingredients. To change them, tell the chat, e.g. "update my {food.name} recipe: 10 ml oil instead of 5".</p>}
      {error && <p className="error">{error}</p>}
      <div className="food-edit-actions">
        <button className="primary" disabled={busy}>{busy ? "Saving…" : "Save"}</button>
        <button type="button" className="ghost" onClick={onCancel}>Cancel</button>
      </div>
    </form>
  );
}

function FoodRow({ food, onChanged, onDeleted }: { food: Food; onChanged: (f: Food) => void; onDeleted: (id: number) => void }) {
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

  return (
    <li className={`food-row ${food.kind}${editing ? " editing" : ""}`}>
      <div className="food-main">
        <div className="food-title">
          <span className="food-name">{food.name}</span>
          {food.brand_name && <span className="muted"> · {food.brand_name}</span>}
          {food.kind === "recipe" && <span className="source-tag recipe">recipe</span>}
        </div>
        <div className="food-nutrients">
          <MacroChips n={food} label={`${food.measures}:`} />
        </div>
        <div className="muted small">
          {SOURCE_LABEL[food.source]}{food.kind === "recipe" && yieldText(food) ? ` · ${yieldText(food)}` : ""}
        </div>
      </div>
      <div className="food-actions">
        {food.kind === "recipe" && (
          <button className="ghost" onClick={() => setOpen(!open)} aria-expanded={open}>
            {open ? "Hide" : "Ingredients"}
          </button>
        )}
        <button className={`ghost icon-btn ${editing ? "on" : ""}`} onClick={() => setEditing(!editing)}
                aria-label={`${editing ? "Close editing" : "Edit"} ${food.name}`} title={editing ? "Close" : "Edit"} aria-pressed={editing}>
          <PencilIcon />
        </button>
        <button className="ghost icon-btn danger" onClick={remove} aria-label={`Delete ${food.name}`} title="Delete">
          <TrashIcon />
        </button>
      </div>
      {error && <p className="error small food-error">{error}</p>}
      {open && food.ingredients && (
        <ul className="ingredient-list">
          {food.ingredients.map((i) => (
            <li key={i.food_id}>
              <span>{i.quantity} {i.unit} {i.name}</span>
              <span className="muted num">{i.calories == null ? "–" : `${Math.round(i.calories)} kcal`}</span>
            </li>
          ))}
        </ul>
      )}
      {editing && (
        <EditForm food={food} onCancel={() => setEditing(false)} onSaved={(f) => { onChanged(f); setEditing(false); }} />
      )}
    </li>
  );
}

export default function FoodsPage({ dataVersion }: { dataVersion: number }) {
  const [foods, setFoods] = useState<Food[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [query, setQuery] = useState("");
  const [filter, setFilter] = useState<Filter>("all");

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
          <h2>My foods</h2>
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
            onChanged={(nf) => setFoods((fs) => fs?.map((x) => (x.id === nf.id ? nf : x)) ?? null)}
            onDeleted={(id) => setFoods((fs) => fs?.filter((x) => x.id !== id) ?? null)}
          />
        ))}
      </ul>
    </section>
  );
}
