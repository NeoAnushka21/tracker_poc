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
# Used once at startup to create the admin account if it doesn't exist yet. Change the
# password afterwards in Settings; later edits to this value don't touch an existing account.
ADMIN_INITIAL_PASSWORD = os.getenv("ADMIN_INITIAL_PASSWORD", "")
ADMIN_EMAILS = {
    e.strip().lower() for e in os.getenv("ADMIN_EMAILS", DEFAULT_ADMIN_EMAIL).split(",") if e.strip()
}

# Product names (not final). The app is OmniAI; MacBro is the chat assistant, named only in the chat.
APP_NAME = "OmniAI"
BOT_NAME = "MacBro"

# Shown at sign-up; bump the version when the wording changes so users are asked again.
CONSENT_VERSION = "2026-09-28.2"   # .2: added third-party AI processing
CONSENT_TEXT = (
    "By creating an account and logging in, you agree that the information you share with "
    f"{APP_NAME} (your email, profile details, food and water logs, and chat messages) is stored "
    "and used to give you recommendations and to improve and develop the application. "
    "The app's administrators can view this data for those purposes. "
    "To reply to your chat messages, they and the related context (such as your targets, today's "
    "logs and saved foods) are sent to third-party AI services that run open-source models; "
    "these services process them under their own terms and may keep them for a limited time."
)

# "anthropic" (Claude) or "openai_compatible" (Groq, Gemini, OpenRouter, Ollama, ...)
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "anthropic")
_IS_ANTHROPIC = LLM_PROVIDER == "anthropic"

LLM_MODEL = os.getenv("LLM_MODEL", "claude-sonnet-5" if _IS_ANTHROPIC else "openai/gpt-oss-120b")
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://api.groq.com/openai/v1")  # openai_compatible only
LLM_API_KEY = os.getenv("LLM_API_KEY", "")                                  # openai_compatible only
LLM_EFFORT = os.getenv("LLM_EFFORT", "medium" if _IS_ANTHROPIC else "low")  # reasoning effort
LLM_MAX_TOKENS = int(os.getenv("LLM_MAX_TOKENS", "16000" if _IS_ANTHROPIC else "4096"))
# Users see a friendly "servers are down" message when the LLM fails; the real reason is
# logged. Set true in development to show the real reason in the chat instead.
SHOW_LLM_ERRORS = os.getenv("SHOW_LLM_ERRORS", "false").lower() == "true"
LLM_UNAVAILABLE_MESSAGE = "MacBro's servers are temporarily down. Please try again in a little while."
LLM_MAX_TOOL_ROUNDS = 8          # safety cap on the tool loop per user message

# --- Multi-model routing (docs/llm-routing-strategy.md) ----------------------
# Two tiers on the same provider by default: a small, fast model for simple messages and a
# large one for complex ones. Each model has its own free quota. Comma-separated lists.
LLM_SMALL_MODELS = [m.strip() for m in os.getenv(
    "LLM_SMALL_MODELS", LLM_MODEL if _IS_ANTHROPIC else "openai/gpt-oss-20b").split(",") if m.strip()]
LLM_LARGE_MODELS = [m.strip() for m in os.getenv("LLM_LARGE_MODELS", LLM_MODEL).split(",") if m.strip()]
# Extra providers (e.g. a second free host for failover): a JSON file, see llm_pool.example.json.
LLM_POOL_FILE = os.getenv("LLM_POOL_FILE", str(Path(__file__).resolve().parent.parent / "llm_pool.json"))
LLM_ROUTING = os.getenv("LLM_ROUTING", "true").lower() == "true"       # false: always the large tier
LLM_FASTPATH = os.getenv("LLM_FASTPATH", "true").lower() == "true"     # rule-based replies without an LLM
LLM_SMALL_HISTORY_MESSAGES = 6     # the small tier gets a shorter history
LLM_ESCALATE_AFTER_ERRORS = 2      # validation errors on the small tier before switching to the large one
LLM_RATE_LIMIT_COOLDOWN_S = 60     # when a 429 doesn't say how long to wait
LLM_FAILURE_COOLDOWN_S = 300       # after LLM_FAILURES_BEFORE_COOLDOWN errors in a row
LLM_FAILURES_BEFORE_COOLDOWN = 3

# Open source only: a model is used only if its licence is in the allowed list. Licences are
# matched by model-name prefix, the longest prefix winning, so versions with different
# licences are told apart (e.g. GLM-5.3 has a custom licence but GLM-5.3-Flash is MIT).
# Families with restrictive licences (Llama, Gemma, Nemotron) are caught anywhere in the name,
# so fine-tunes built on them are too. Unknown models get no licence and are blocked.
# Check a new model's licence (e.g. on its Hugging Face page) before adding it here.
MODEL_LICENSES = {
    "gpt-oss": "Apache-2.0",
    "qwen3": "Apache-2.0",
    "qwen2.5": "Apache-2.0",
    "qwen2.5-72b": "Qwen License",
    "qwen2.5-3b": "Qwen License",
    "mistral-7b": "Apache-2.0",
    "mistral-small": "Apache-2.0",
    "mistral-nemo": "Apache-2.0",
    "mixtral": "Apache-2.0",
    "mistral-large": "Mistral Research License",
    "mistral-medium": "Proprietary",
    "codestral": "Mistral Non-Production License",
    "deepseek-v3": "MIT",
    "deepseek-r1": "MIT",
    "deepseek-v4": "MIT",
    "deepseek-chat": "MIT",
    "deepseek-coder": "DeepSeek License",
    "deepseek-v2": "DeepSeek License",
    "glm-4.5": "MIT",
    "glm-4.6": "MIT",
    "glm-5.2": "MIT",
    "glm-5.3": "GLM-5.3 License",
    "glm-5.3-flash": "MIT",
    "granite": "Apache-2.0",
    "phi-3": "MIT",
    "phi-4": "MIT",
    "kimi": "Modified MIT",
    # restrictive families, matched anywhere in the name
    "llama": "Llama Community License",
    "gemma": "Gemma Terms of Use",
    "nemotron": "NVIDIA Open Model License",
    "minitron": "NVIDIA Open Model License",
}
RESTRICTIVE_FAMILIES = ("llama", "gemma", "nemotron", "minitron")
ALLOWED_MODEL_LICENSES = {s.strip() for s in os.getenv(
    "ALLOWED_MODEL_LICENSES", "Apache-2.0,MIT").split(",") if s.strip()}
# Past chat messages sent as context. Kept smaller for free tiers with tight token/minute limits.
# The chat starts fresh each local day; messages from the last few hours before midnight are
# still sent to the model so a conversation that crosses midnight keeps its context.
CHAT_DAY_GRACE_HOURS = 3
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

# --- Body profile (optional measurements, stored in cm) --------------------
BODY_PARTS = [
    ("neck_cm", "Neck"), ("chest_cm", "Chest"), ("waist_cm", "Waist"), ("hips_cm", "Hips"),
    ("biceps_cm", "Biceps"), ("forearm_cm", "Forearm"), ("thigh_cm", "Thigh"), ("calf_cm", "Calf"),
]
BODY_PART_KEYS = [k for k, _ in BODY_PARTS]

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
