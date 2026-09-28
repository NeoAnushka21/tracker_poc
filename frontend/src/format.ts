export const GOALS: Record<string, string> = {
  weight_loss: "Lose weight",
  muscle_gain: "Build muscle",
  weight_gain: "Gain weight",
  recomposition: "Recomposition (lose fat, keep/build muscle)",
  maintenance: "Maintain weight",
};

export const ACTIVITY: Record<string, string> = {
  sedentary: "Sedentary: desk job, little exercise",
  light: "Light: exercise 1–3 days/week",
  moderate: "Moderate: exercise 3–5 days/week",
  active: "Active: exercise 6–7 days/week",
  very_active: "Very active: hard training or physical job",
};

export const MEAL_ORDER = ["breakfast", "morning_snack", "lunch", "evening_snack", "dinner"];

export const MEAL_LABEL: Record<string, string> = {
  breakfast: "Breakfast",
  morning_snack: "Morning snack",
  lunch: "Lunch",
  evening_snack: "Evening snack",
  dinner: "Dinner",
  snack: "Snack",
};

export function litres(ml: number): string {
  return `${(Math.round(ml / 100) / 10).toFixed(1)} L`;
}

export const kcal = (n: number) => `${Math.round(n)} kcal`;
export const grams = (n: number) => `${Math.round(n * 10) / 10}g`;
export const time = (localIso: string) => localIso.slice(11, 16);

export function friendlyDate(localIso: string, today: string): string {
  const day = localIso.slice(0, 10);
  if (day === today) return "Today";
  const d = new Date(`${day}T00:00:00`);
  return d.toLocaleDateString(undefined, { weekday: "short", day: "numeric", month: "short" });
}

export function shiftDay(day: string, delta: number): string {
  const d = new Date(`${day}T12:00:00`);
  d.setDate(d.getDate() + delta);
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
}
