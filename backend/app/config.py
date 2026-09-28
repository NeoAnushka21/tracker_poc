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
    ("breakfast", 5, 11),
    ("lunch", 11, 15),
    ("snack", 15, 19),
    ("dinner", 19, 23),
]
MEAL_FALLBACK = "snack"  # 23:00-05:00
MEAL_TYPES = ["breakfast", "lunch", "dinner", "snack"]

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
