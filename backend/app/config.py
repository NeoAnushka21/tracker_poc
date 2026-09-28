"""App settings (from environment) and tunable constants.

Everything a product decision might change later lives here, so it can be
tuned without touching logic.
"""
import os
from pathlib import Path

from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BACKEND_DIR / ".env")

# --- Environment ---------------------------------------------------------
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{BACKEND_DIR / 'macro_tracker.db'}")
SECRET_KEY = os.getenv("SECRET_KEY", "dev-only-insecure-secret-change-me-in-backend-env")
SESSION_DAYS = int(os.getenv("SESSION_DAYS", "14"))
COOKIE_SECURE = os.getenv("COOKIE_SECURE", "false").lower() == "true"
# Comma-separated emails that get the admin panel. Nobody else can see or call it.
DEFAULT_ADMIN_EMAIL = "mhatre.anushka.work@gmail.com"
ADMIN_EMAILS = {
    e.strip().lower() for e in os.getenv("ADMIN_EMAILS", DEFAULT_ADMIN_EMAIL).split(",") if e.strip()
}

# Shown at sign-up; bump the version when the wording changes so users are asked again.
CONSENT_VERSION = "2026-09-28"
CONSENT_TEXT = (
    "By creating an account and logging in, you agree that the information you share with "
    "MacBro (your email, profile details, food and water logs, and chat messages) is stored "
    "and used to give you recommendations and to improve and develop the application. "
    "The app's administrators can view this data for those purposes."
)

# "anthropic" (Claude) or "openai_compatible" (Groq, Gemini, OpenRouter, Ollama, ...)
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "anthropic")
_IS_ANTHROPIC = LLM_PROVIDER == "anthropic"

LLM_MODEL = os.getenv("LLM_MODEL", "claude-sonnet-5" if _IS_ANTHROPIC else "openai/gpt-oss-120b")
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://api.groq.com/openai/v1")  # openai_compatible only
LLM_API_KEY = os.getenv("LLM_API_KEY", "")                                  # openai_compatible only
LLM_EFFORT = os.getenv("LLM_EFFORT", "medium" if _IS_ANTHROPIC else "low")  # reasoning effort
LLM_MAX_TOKENS = int(os.getenv("LLM_MAX_TOKENS", "16000" if _IS_ANTHROPIC else "4096"))
LLM_MAX_TOOL_ROUNDS = 8          # safety cap on the tool loop per user message
# Past chat messages sent as context. Kept smaller for free tiers with tight token/minute limits.
CHAT_HISTORY_MESSAGES = int(os.getenv("CHAT_HISTORY_MESSAGES", "30" if _IS_ANTHROPIC else "12"))

# --- Meal-type inference (user's local time, [start, end) hours) ----------
MEAL_WINDOWS = [
    ("breakfast", 5, 10),
    ("morning_snack", 10, 12),
    ("lunch", 12, 15),
    ("evening_snack", 15, 19),
    ("dinner", 19, 23),
]
MEAL_FALLBACK = "evening_snack"  # late night, 23:00-05:00
MEAL_TYPES = ["breakfast", "morning_snack", "lunch", "evening_snack", "dinner"]
SNACK_TYPES = ("morning_snack", "evening_snack")
LEGACY_SNACK = "snack"           # older entries; relabelled at startup

# --- Water ---------------------------------------------------------------
WATER_ML_PER_KG = 35             # common hydration guideline for drinking water
WATER_ACTIVITY_EXTRA_ML = {"sedentary": 0, "light": 250, "moderate": 500, "active": 750, "very_active": 1000}
WATER_MAX_LOG_ML = 5000          # sanity cap for a single water log

# --- Pending proposals ---------------------------------------------------
PENDING_TTL_HOURS = 24

# --- Target calculation --------------------------------------------------
ACTIVITY_FACTORS = {
    "sedentary": 1.2,        # desk job, little exercise
    "light": 1.375,          # 1-3 sessions/week
    "moderate": 1.55,        # 3-5 sessions/week
    "active": 1.725,         # 6-7 sessions/week
    "very_active": 1.9,      # hard training or physical job
}

# goal -> (calorie multiplier vs TDEE, protein g per kg bodyweight)
GOAL_SETTINGS = {
    "weight_loss": (0.80, 2.0),
    "recomposition": (0.90, 2.2),
    "muscle_gain": (1.10, 2.0),
    "weight_gain": (1.10, 1.8),
    "maintenance": (1.00, 1.8),
}
FAT_CALORIE_SHARE = 0.25
KCAL_PER_G = {"protein": 4, "carbs": 4, "fat": 9}
FIBER_G_PER_1000_KCAL = 14       # dietary guideline: 14 g fiber per 1,000 kcal

# --- Micronutrients ------------------------------------------------------
# Daily reference values for adults (US Dietary Reference Intakes: RDA, or AI where no
# RDA exists). Values by sex and age band: [(max_age_inclusive, male, female), ...].
# "limit" nutrients are daily maximums (staying under is the goal), not targets.
MICRONUTRIENTS = [
    # key, label, unit, kind, [(max_age, male, female)]
    ("iron_mg", "Iron", "mg", "target", [(50, 8, 18), (200, 8, 8)]),
    ("calcium_mg", "Calcium", "mg", "target", [(50, 1000, 1000), (70, 1000, 1200), (200, 1200, 1200)]),
    ("magnesium_mg", "Magnesium", "mg", "target", [(30, 400, 310), (200, 420, 320)]),
    ("potassium_mg", "Potassium", "mg", "target", [(200, 3400, 2600)]),
    ("zinc_mg", "Zinc", "mg", "target", [(200, 11, 8)]),
    ("vitamin_c_mg", "Vitamin C", "mg", "target", [(200, 90, 75)]),
    ("vitamin_b12_mcg", "Vitamin B12", "mcg", "target", [(200, 2.4, 2.4)]),
    ("vitamin_d_mcg", "Vitamin D", "mcg", "target", [(70, 15, 15), (200, 20, 20)]),
    ("sodium_mg", "Sodium", "mg", "limit", [(200, 2300, 2300)]),
]
MICRONUTRIENT_KEYS = [m[0] for m in MICRONUTRIENTS]

# --- Dashboard adherence (used by weekly/monthly views, later phase) -----
ADHERENCE_CALORIE_TOLERANCE = 0.10
ADHERENCE_MIN_PROTEIN_SHARE = 0.90
