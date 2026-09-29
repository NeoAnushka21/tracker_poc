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
  fiber_g: number;
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
  consented: boolean;
  is_admin: boolean;
  created_at: string | null;
  last_login_at: string | null;
  consented_at: string | null;
  guide_seen: boolean;
};

export type Item = Nutrients & {
  id?: number;
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
  /** "dashboard": an AI estimate from the dashboard's Add food, not a chat card. */
  origin?: "dashboard";
  items?: Item[];
  totals?: Nutrients;
  entry_id?: number;
  before?: Entry;
  // move / copy
  from_meal_type?: string;
  to_meal_type?: string;
  to_date?: string | null;
  // water
  amount_ml?: number;
  drank_at?: string;
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
  action_type: "create" | "edit" | "delete" | "save_recipe" | "water" | "move" | "copy";
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
  kind?: "progress" | null;
  /** Progress card numbers (kind "progress"), or the day picked for a user message. */
  data?: (ProgressData & { log_date?: undefined }) | { log_date?: string } | null;
};

export type ChatDay = { day: string; messages: ChatMessage[]; prev_day: string | null };

/** The card posted after a confirmed log: macros after food, water after water. `date`/`is_today`
 *  are missing on cards saved before 2026-09-29 (those were always macros, for today). */
type ProgressDay = { date?: string; is_today?: boolean; headline: string };
export type MacroProgressData = ProgressDay & {
  focus?: "macros";
  calories: { consumed: number; target: number | null; pct: number | null };
  macros: { key: string; label: string; consumed: number; target: number | null; pct: number | null }[];
  water: { consumed_ml: number; target_ml: number | null };
  meals_logged: number;
};
export type WaterProgressData = ProgressDay & {
  focus: "water";
  water: { consumed_ml: number; target_ml: number | null; pct: number | null; logs: number };
};
export type ProgressData = MacroProgressData | WaterProgressData;

export type DailySummary = {
  date: string;
  targets: Targets | null;
  consumed: Nutrients;
  remaining: Nutrients | null;
  micronutrients: MicroSummary;
  water: WaterSummary;
  entries: Entry[];
};

export type WaterSummary = {
  target_ml: number | null;
  consumed_ml: number;
  logs: { id: number; amount_ml: number; drank_at: string }[];
};

export type Micronutrient = {
  key: string;
  label: string;
  unit: string;
  kind: "target" | "limit";
  target: number;
  consumed: number;
};

export type MicroSummary = {
  items_total: number;
  items_with_data: number;
  nutrients: Micronutrient[];
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
  /** Units it can be logged in (reference unit, g when its weight is known, piece, serving). */
  units: string[];
  last_used_at: string;
  /** Per the reference amount (`measures`), e.g. {"iron_mg": 0.4}; missing keys are unknown. */
  micronutrients: Record<string, number> | null;
  ingredients?: RecipeIngredient[];
};

/** A micronutrient a food can carry (GET /api/foods/micronutrients). */
export type MicroField = { key: string; label: string; unit: string; kind: "target" | "limit" };

export type RangeDay = Nutrients & {
  date: string;
  logged: boolean;
  water_ml: number;
  targets: Targets | null;
  on_target: boolean | null;
};

export type RangeSummary = {
  start: string;
  end: string;
  days: RangeDay[];
  water_target_ml: number | null;
  summary: {
    days_in_range: number;
    days_logged: number;
    days_on_target: number;
    avg: Record<keyof Nutrients | "water_ml", number | null>;
    macro_split_pct: { protein: number | null; carbs: number | null; fat: number | null };
    kcal_by_meal: Record<string, number>;
    adherence_rule: { calorie_tolerance_pct: number; min_protein_pct: number };
  };
};

export type AdminUserRow = {
  id: number;
  email: string;
  preferred_name: string | null;
  created_at: string | null;
  last_login_at: string | null;
  login_count: number;
  consented_at: string | null;
  onboarded: boolean;
  goal_type: string | null;
  entries: number;
  foods: number;
  water_logs: number;
  chat_messages: number;
  last_logged_at: string | null;
};

export type AdminUserDetail = {
  profile: User & { created_at: string | null; last_login_at: string | null; consented_at: string | null };
  weights: { weight_kg: number; logged_at: string }[];
  days: { date: string; entries: Entry[]; totals: Nutrients }[];
  foods: Food[];
};

export type AuditRow = { at: string; admin: string | null; action: string; user: string | null };

export type Streak = { current: number; best: number; today_done: boolean };

export type Streaks = {
  logging: Streak;
  /** Days in a row with protein at least `rule.min_protein_pct` % of the target. */
  protein: Streak;
  last_7_days: { date: string; logged: boolean; protein_hit: boolean }[];
  rule: { min_protein_pct: number };
};

export type LlmUsageReport = {
  hours: number;
  totals: {
    user_messages: number; model_calls: number; fastpath_replies: number; fastpath_share_pct: number | null;
    tokens: number; errors: number; rate_limited: number; escalations: number;
  };
  by_model: {
    provider: string; model: string; tier: string; calls: number; ok: number; errors: number; rate_limited: number;
    prompt_tokens: number; completion_tokens: number; avg_latency_ms: number | null;
  }[];
  by_intent: { intent: string; calls: number; tokens: number }[];
  fastpath: Record<string, number>;
  pool: {
    provider?: string; model?: string; tier?: string; license?: string | null; available?: boolean;
    cooldown_seconds?: number; consecutive_failures?: number; last_error?: string | null; error?: string;
  }[];
};
