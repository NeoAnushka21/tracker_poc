export type Nutrients = {
  calories: number;
  protein_g: number;
  carbs_g: number;
  fat_g: number;
  fiber_g: number;
};

export type Targets = {
  calories: number;
  protein_g: number;
  carbs_g: number;
  fat_g: number;
  effective_date: string;
  is_custom: boolean;
};

export type User = {
  id: number;
  email: string;
  onboarded: boolean;
  preferred_name: string | null;
  date_of_birth: string | null;
  sex: "male" | "female" | null;
  height_cm: number | null;
  weight_kg: number | null;
  unit_system: "metric" | "imperial";
  timezone: string;
  goal_type: string | null;
  activity_level: string | null;
  targets: Targets | null;
};

export type Item = Nutrients & {
  ingredient_name: string;
  brand_name: string | null;
  quantity: number;
  unit: string;
  food_id?: number | null;
  source?: "estimate" | "library" | "recipe";
};

export type Entry = {
  id: number;
  eaten_at: string; // local "YYYY-MM-DDTHH:MM"
  meal_type: string;
  items: Item[];
  totals: Nutrients;
};

export type ActionPayload = {
  summary: string;
  eaten_at?: string;
  meal_type?: string;
  meal_type_source?: "stated" | "inferred";
  items?: Item[];
  totals?: Nutrients;
  entry_id?: number;
  before?: Entry;
  // save_recipe
  name?: string;
  replaces_recipe_id?: number | null;
  ingredients?: Item[];
  yield_pieces?: number | null;
  yield_servings?: number | null;
  cooked_weight_g?: number | null;
  ref_qty?: number;
  ref_unit?: string;
  per_ref?: Nutrients;
  batch_totals?: Nutrients;
};

export type Action = {
  id: number;
  action_type: "create" | "edit" | "delete" | "save_recipe";
  status: "pending" | "confirmed" | "rejected" | "superseded" | "expired";
  target_entry_id: number | null;
  result_entry_id: number | null;
  payload: ActionPayload;
};

export type ChatMessage = {
  id: number;
  role: "user" | "assistant" | "event";
  content: string;
  created_at: string;
  actions: Action[];
};

export type DailySummary = {
  date: string;
  targets: Targets | null;
  consumed: Nutrients;
  remaining: Omit<Nutrients, "fiber_g"> | null;
  entries: Entry[];
};

export type RecipeIngredient = Partial<Nutrients> & {
  food_id: number;
  name: string;
  quantity: number;
  unit: string;
};

export type Food = Nutrients & {
  id: number;
  name: string;
  brand_name: string | null;
  kind: "food" | "recipe";
  source: "estimate" | "user" | "recipe";
  ref_qty: number;
  ref_unit: string;
  grams_per_piece: number | null;
  grams_per_serving: number | null;
  yield_pieces: number | null;
  yield_servings: number | null;
  cooked_weight_g: number | null;
  measures: string;
  last_used_at: string;
  ingredients?: RecipeIngredient[];
};
