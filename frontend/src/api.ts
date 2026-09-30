import type {
  Action, AdminUserDetail, AdminUserRow, AuditRow, ChatMessage, DailySummary, Food, Item, RangeSummary, User,
  Streaks, ChatDay, LlmUsageReport, MicroField,
} from "./types";
import { recoverServer, serverAwake, SLOW_REQUEST_MS } from "./wake";

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

async function request<T>(method: string, path: string, body?: unknown, signal?: AbortSignal, retried = false): Promise<T> {
  // A slow request may mean the free server is asleep: if /api/health doesn't answer either,
  // show the WakeScreen until it does (a slow chat reply on an awake server shows nothing).
  const slow = setTimeout(() => { void serverAwake().then((up) => { if (!up) void recoverServer(); }); }, SLOW_REQUEST_MS);
  let res: Response;
  try {
    res = await fetch(path, {
      method,
      signal,
      credentials: "same-origin",
      headers: body !== undefined ? { "Content-Type": "application/json" } : undefined,
      body: body !== undefined ? JSON.stringify(body) : undefined,
    });
  } catch (e) {
    // Retry only when the server really was asleep; otherwise the request may have been processed.
    if (retried || signal?.aborted || (await serverAwake())) throw e;
    await recoverServer();
    return request<T>(method, path, body, signal, true);
  } finally {
    clearTimeout(slow);
  }
  // Every API response is JSON; HTML is Render's "waking up" page, and the backend never saw the request.
  if (!retried && !(res.headers.get("content-type") ?? "").includes("application/json")) {
    await recoverServer();
    return request<T>(method, path, body, signal, true);
  }
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

/** Continue with Google: signed in, or come back with the user's OK (link an existing email account / consent for a new one). */
export type AiAllowance = { limit: number | null; used: number; remaining: number | null; resets_at: string };

export type GoogleLoginResult =
  | { status: "ok"; user: User }
  | { status: "link_required" | "consent_required"; email: string };

/** Dashboard Add food: a saved food is added at once; a near-miss spelling of one asks "Did you mean …?";
 *  any other food comes back as an AI estimate to confirm. */
export type AddFoodResult =
  | { status: "added"; entry_id: number; item: Item }
  | { status: "suggest"; food: { id: number; name: string; units: string[] } }
  | { status: "ask_state"; name: string }
  | { status: "estimate"; source: "ai" | "general"; action: Action; note: string }
  | { status: "no_estimate"; message: string };

/** BMI with WHO adult categories, or which inputs are missing. */
export type Bmi =
  | { status: "ok"; value: number; category: string; note: string }
  | { status: "missing"; missing: string[] };
/** US Navy body-fat estimate: a number only when every input is present and the result is plausible. */
export type BodyFat =
  | { status: "ok"; value: number; method: string; typical_error: number; warning?: string }
  | { status: "missing"; missing: string[]; method: string }
  | { status: "implausible"; reason: string; method: string };

export type BodyProfileData = {
  sex: "male" | "female" | null;
  height_cm: number | null;
  weight_kg: number | null;
  bmi: Bmi;
  body_fat: BodyFat;
  weight_history: { weight_kg: number; logged_at: string }[];
  latest: { key: string; label: string; tip: string; value_cm: number | null; measured_at: string | null; change_cm: number | null }[];
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
  /** Per the same reference amount; missing keys are "unknown". */
  micronutrients: Record<string, number>;
};

export const api = {
  me: () => request<User>("GET", "/api/auth/me"),
  register: (email: string, password: string, consent: boolean) =>
    request<User>("POST", "/api/auth/register", { email, password, consent }),
  /** Once two-step sign-in is on, the first try fails with "code_required"; send it again with the code. */
  adminLogin: (email: string, password: string, code?: string) =>
    request<User>("POST", "/api/auth/admin-login", { email, password, code: code || null }),
  adminTotp: () => request<{ enabled: boolean }>("GET", "/api/admin/totp"),
  adminTotpSetup: () => request<{ secret: string; uri: string; qr_svg_data_uri: string }>("POST", "/api/admin/totp/setup"),
  adminTotpEnable: (code: string) => request<{ enabled: boolean }>("POST", "/api/admin/totp/enable", { code }),
  adminTotpDisable: (password: string, code: string) =>
    request<{ enabled: boolean }>("POST", "/api/admin/totp/disable", { password, code }),
  changePassword: (current_password: string, new_password: string) =>
    request<{ ok: boolean }>("POST", "/api/auth/change-password", { current_password, new_password }),
  /** Password accounts confirm with the password; Google-only accounts type their email. */
  deleteAccount: (password: string, confirm_email = "") =>
    request<{ ok: boolean }>("POST", "/api/auth/delete-account", { password, confirm_email }),
  /** Download my data: everything stored about the account (DPDP right of access). */
  exportData: () => request<Record<string, unknown>>("GET", "/api/profile/export"),
  authOptions: () => request<{ google_client_id: string | null; password_reset: boolean }>("GET", "/api/auth/options"),
  /** Always answers the same message, whether or not the account exists. */
  forgotPassword: (email: string) => request<{ ok: boolean; message: string }>("POST", "/api/auth/forgot-password", { email }),
  resetPassword: (token: string, new_password: string) =>
    request<{ ok: boolean }>("POST", "/api/auth/reset-password", { token, new_password }),
  googleLogin: (credential: string, flags: { consent?: boolean; link?: boolean } = {}) =>
    request<GoogleLoginResult>("POST", "/api/auth/google", { credential, ...flags }),
  consentText: () => request<{ version: string; text: string }>("GET", "/api/auth/consent-text"),
  giveConsent: () => request<User>("POST", "/api/auth/consent"),
  guideSeen: () => request<User>("POST", "/api/auth/guide-seen"),
  login: (email: string, password: string) => request<User>("POST", "/api/auth/login", { email, password }),
  logout: () => request<{ ok: boolean }>("POST", "/api/auth/logout"),
  /** Ends every session of the account, on all devices (this one too). */
  logoutEverywhere: () => request<{ ok: boolean }>("POST", "/api/auth/logout-everywhere"),

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
  /** Fix a saved set; the body is the whole set (null clears a value). */
  editMeasurement: (id: number, values: Record<string, number | null>) =>
    request<BodyProfileData>("PUT", `/api/profile/measurements/${id}`, values),

  chatDay: (day?: string) => request<ChatDay>("GET", `/api/chat/day${day ? `?day=${day}` : ""}`),
  send: (message: string, feedback_on_action_id: number | null, client_request_id: string, signal?: AbortSignal,
         log_date?: string | null) =>
    request<ChatMessage[]>("POST", "/api/chat", { message, feedback_on_action_id, client_request_id, log_date: log_date ?? null }, signal),
  /** Today's AI allowance; limit/remaining are null when unlimited. */
  aiAllowance: () => request<AiAllowance>("GET", "/api/chat/allowance"),
  cancelChat: (client_request_id: string) =>
    request<{ status: "cancelled" | "finished" }>("POST", "/api/chat/cancel", { client_request_id }),
  transferItem: (itemId: number, to_meal_type: string, mode: "move" | "copy", to_date?: string) =>
    request<{ ok: boolean; entry_id: number }>("POST", `/api/entries/items/${itemId}/transfer`, { to_meal_type, mode, to_date }),
  setItemQuantity: (itemId: number, quantity: number) =>
    request<{ ok: boolean }>("PATCH", `/api/entries/items/${itemId}`, { quantity }),
  deleteItem: (itemId: number) => request<{ ok: boolean }>("DELETE", `/api/entries/items/${itemId}`),
  addFood: (body: { name: string; quantity: number; unit: string; meal_type: string; day: string; food_id: number | null;
             as_typed?: boolean }) =>
    request<AddFoodResult>("POST", "/api/entries/add", body),
  confirm: (id: number) => request<ActionResult>("POST", `/api/actions/${id}/confirm`),
  reject: (id: number) => request<ActionResult>("POST", `/api/actions/${id}/reject`),

  foods: () => request<Food[]>("GET", "/api/foods"),
  micronutrientFields: () => request<MicroField[]>("GET", "/api/foods/micronutrients"),
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
