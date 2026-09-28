import type {
  Action, AdminUserDetail, AdminUserRow, AuditRow, ChatMessage, DailySummary, Food, RangeSummary, User,
  Streaks, ChatDay, LlmUsageReport,
} from "./types";

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

async function request<T>(method: string, path: string, body?: unknown, signal?: AbortSignal): Promise<T> {
  const res = await fetch(path, {
    method,
    signal,
    credentials: "same-origin",
    headers: body !== undefined ? { "Content-Type": "application/json" } : undefined,
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });
  if (!res.ok) {
    let message = `Request failed (${res.status})`;
    try {
      const data = await res.json();
      if (typeof data.detail === "string") message = data.detail;
      else if (Array.isArray(data.detail) && data.detail[0]?.msg) message = data.detail[0].msg.replace(/^Value error, /, "");
    } catch {
      /* non-JSON error body */
    }
    throw new ApiError(res.status, message);
  }
  return res.json() as Promise<T>;
}

export type OnboardingInput = {
  preferred_name: string | null;
  date_of_birth: string;
  sex: "male" | "female";
  height_cm: number;
  weight_kg: number;
  unit_system: "metric" | "imperial";
  timezone: string;
  goal_type: string;
  activity_level: string;
};

export type TargetsInput = {
  daily_calorie_target: number;
  protein_target_g: number;
  carbs_target_g: number;
  fat_target_g: number;
};

type ActionResult = { action: Action; event: ChatMessage; progress: ChatMessage | null };

export type BodyProfileData = {
  height_cm: number | null;
  weight_kg: number | null;
  weight_history: { weight_kg: number; logged_at: string }[];
  latest: { key: string; label: string; value_cm: number | null; measured_at: string | null; change_cm: number | null }[];
  history: ({ id: number; measured_at: string } & Record<string, number | string | null>)[];
};

export type FoodInput = {
  name: string;
  brand_name: string | null;
  ref_qty: number;
  ref_unit: string;
  calories: number;
  protein_g: number;
  carbs_g: number;
  fat_g: number;
  fiber_g: number;
  grams_per_piece: number | null;
  grams_per_serving: number | null;
};

export const api = {
  me: () => request<User>("GET", "/api/auth/me"),
  register: (email: string, password: string, consent: boolean) =>
    request<User>("POST", "/api/auth/register", { email, password, consent }),
  adminLogin: (email: string, password: string) => request<User>("POST", "/api/auth/admin-login", { email, password }),
  changePassword: (current_password: string, new_password: string) =>
    request<{ ok: boolean }>("POST", "/api/auth/change-password", { current_password, new_password }),
  deleteAccount: (password: string) => request<{ ok: boolean }>("POST", "/api/auth/delete-account", { password }),
  consentText: () => request<{ version: string; text: string }>("GET", "/api/auth/consent-text"),
  giveConsent: () => request<User>("POST", "/api/auth/consent"),
  guideSeen: () => request<User>("POST", "/api/auth/guide-seen"),
  login: (email: string, password: string) => request<User>("POST", "/api/auth/login", { email, password }),
  logout: () => request<{ ok: boolean }>("POST", "/api/auth/logout"),

  onboarding: (data: OnboardingInput) =>
    request<User & { calculation: { bmr: number; tdee: number } }>("POST", "/api/profile/onboarding", data),
  updateTargets: (data: TargetsInput) => request<User>("PUT", "/api/profile/targets", data),
  logWeight: (weight_kg: number, recalculate_targets: boolean) =>
    request<User>("POST", "/api/profile/weight", { weight_kg, recalculate_targets }),

  getBody: () => request<BodyProfileData>("GET", "/api/profile/body"),
  updateHeight: (height_cm: number, recalculate_targets: boolean) =>
    request<User>("POST", "/api/profile/height", { height_cm, recalculate_targets }),
  addMeasurements: (values: Record<string, number>) => request<BodyProfileData>("POST", "/api/profile/measurements", values),
  deleteMeasurement: (id: number) => request<BodyProfileData>("DELETE", `/api/profile/measurements/${id}`),

  chatDay: (day?: string) => request<ChatDay>("GET", `/api/chat/day${day ? `?day=${day}` : ""}`),
  send: (message: string, feedback_on_action_id: number | null, client_request_id: string, signal?: AbortSignal,
         log_date?: string | null) =>
    request<ChatMessage[]>("POST", "/api/chat", { message, feedback_on_action_id, client_request_id, log_date: log_date ?? null }, signal),
  cancelChat: (client_request_id: string) =>
    request<{ status: "cancelled" | "finished" }>("POST", "/api/chat/cancel", { client_request_id }),
  transferItem: (itemId: number, to_meal_type: string, mode: "move" | "copy", to_date?: string) =>
    request<{ ok: boolean; entry_id: number }>("POST", `/api/entries/items/${itemId}/transfer`, { to_meal_type, mode, to_date }),
  setItemQuantity: (itemId: number, quantity: number) =>
    request<{ ok: boolean }>("PATCH", `/api/entries/items/${itemId}`, { quantity }),
  deleteItem: (itemId: number) => request<{ ok: boolean }>("DELETE", `/api/entries/items/${itemId}`),
  confirm: (id: number) => request<ActionResult>("POST", `/api/actions/${id}/confirm`),
  reject: (id: number) => request<ActionResult>("POST", `/api/actions/${id}/reject`),

  foods: () => request<Food[]>("GET", "/api/foods"),
  updateFood: (id: number, data: FoodInput) => request<Food>("PUT", `/api/foods/${id}`, data),
  deleteFood: (id: number) => request<{ ok: boolean }>("DELETE", `/api/foods/${id}`),

  addWater: (amount_ml: number) => request<{ id: number; amount_ml: number }>("POST", "/api/water", { amount_ml }),
  deleteWater: (id: number) => request<{ ok: boolean }>("DELETE", `/api/water/${id}`),

  range: (days: number) => request<RangeSummary>("GET", `/api/dashboard/range?days=${days}`),

  adminUsers: () => request<AdminUserRow[]>("GET", "/api/admin/users"),
  adminUser: (id: number, days = 14) => request<AdminUserDetail>("GET", `/api/admin/users/${id}?days=${days}`),
  adminChat: (id: number) => request<ChatMessage[]>("GET", `/api/admin/users/${id}/chat`),
  adminAudit: () => request<AuditRow[]>("GET", "/api/admin/audit"),
  adminLlmUsage: (hours = 24) => request<LlmUsageReport>("GET", `/api/admin/llm-usage?hours=${hours}`),

  streaks: () => request<Streaks>("GET", "/api/dashboard/streaks"),
  daily: (day?: string) => request<DailySummary>("GET", `/api/dashboard/daily${day ? `?day=${day}` : ""}`),
};
