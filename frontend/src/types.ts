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
};

export type Action = {
  id: number;
  action_type: "create" | "edit" | "delete";
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
