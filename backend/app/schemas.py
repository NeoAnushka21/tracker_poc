from datetime import date
from typing import Literal

from pydantic import BaseModel, Field, field_validator

from app.config import ACTIVITY_FACTORS, GOAL_SETTINGS

Sex = Literal["male", "female"]
UnitSystem = Literal["metric", "imperial"]


class Credentials(BaseModel):
    email: str = Field(min_length=3, max_length=255)
    password: str = Field(min_length=8, max_length=200)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, v: str) -> str:
        v = v.strip().lower()
        if "@" not in v or "." not in v.split("@")[-1]:
            raise ValueError("Enter a valid email address")
        return v


class AdminLoginIn(Credentials):
    code: str | None = Field(default=None, max_length=10)   # from the authenticator app, once two-step is on


class TotpCodeIn(BaseModel):
    code: str = Field(min_length=6, max_length=10)


class TotpDisableIn(BaseModel):
    password: str = Field(min_length=1, max_length=200)
    code: str = Field(min_length=6, max_length=10)


class PasswordChangeIn(BaseModel):
    # Empty for accounts without a password yet (created with Google): this sets the first one.
    current_password: str = Field(default="", max_length=200)
    new_password: str = Field(min_length=8, max_length=200)


class DeleteAccountIn(BaseModel):
    # Accounts with a password confirm with it; Google-only accounts type their email instead.
    password: str = Field(default="", max_length=200)
    confirm_email: str = Field(default="", max_length=255)


class ForgotPasswordIn(BaseModel):
    email: str = Field(min_length=3, max_length=255)

    @field_validator("email")
    @classmethod
    def normalize(cls, v: str) -> str:
        return v.strip().lower()


class ResetPasswordIn(BaseModel):
    token: str = Field(min_length=20, max_length=200)
    new_password: str = Field(min_length=8, max_length=200)


class GoogleLoginIn(BaseModel):
    credential: str = Field(min_length=20, max_length=5000)   # the ID token from Google's button
    consent: bool = False      # data consent, needed when this creates a new account
    link: bool = False         # the user agreed to link Google to their existing email account


class RegisterIn(Credentials):
    consent: bool = False


class OnboardingIn(BaseModel):
    preferred_name: str | None = Field(default=None, max_length=80)
    date_of_birth: date
    sex: Sex
    height_cm: float = Field(gt=50, lt=280)
    weight_kg: float = Field(gt=20, lt=400)
    unit_system: UnitSystem = "metric"
    timezone: str
    goal_type: str
    activity_level: str
    country: str = Field(min_length=2, max_length=2)      # ISO code from the dropdown
    region: str | None = Field(default=None, max_length=80)

    @field_validator("goal_type")
    @classmethod
    def check_goal(cls, v: str) -> str:
        if v not in GOAL_SETTINGS:
            raise ValueError(f"goal_type must be one of {list(GOAL_SETTINGS)}")
        return v

    @field_validator("activity_level")
    @classmethod
    def check_activity(cls, v: str) -> str:
        if v not in ACTIVITY_FACTORS:
            raise ValueError(f"activity_level must be one of {list(ACTIVITY_FACTORS)}")
        return v


class LocationIn(BaseModel):
    country: str = Field(min_length=2, max_length=2)
    region: str | None = Field(default=None, max_length=80)


class TargetsIn(BaseModel):
    daily_calorie_target: int = Field(ge=800, le=10000)
    protein_target_g: int = Field(ge=0, le=1000)
    carbs_target_g: int = Field(ge=0, le=2000)
    fat_target_g: int = Field(ge=0, le=1000)


class WeightIn(BaseModel):
    weight_kg: float = Field(gt=20, lt=400)
    recalculate_targets: bool = True


class HeightIn(BaseModel):
    height_cm: float = Field(gt=50, lt=280)
    recalculate_targets: bool = True


class MeasurementsIn(BaseModel):
    """All optional; at least one required. Values in cm."""
    neck_cm: float | None = Field(default=None, ge=10, le=250)
    shoulders_cm: float | None = Field(default=None, ge=10, le=250)
    chest_cm: float | None = Field(default=None, ge=10, le=250)
    waist_cm: float | None = Field(default=None, ge=10, le=250)
    hips_cm: float | None = Field(default=None, ge=10, le=250)
    biceps_cm: float | None = Field(default=None, ge=10, le=250)
    forearm_cm: float | None = Field(default=None, ge=10, le=250)
    wrist_cm: float | None = Field(default=None, ge=5, le=250)
    thigh_cm: float | None = Field(default=None, ge=10, le=250)
    calf_cm: float | None = Field(default=None, ge=10, le=250)


class ChatIn(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    # Set when the user clicked "Needs changes" on a proposal and is now typing feedback.
    feedback_on_action_id: int | None = None
    # Lets the browser cancel this turn (Stop button) via /api/chat/cancel.
    client_request_id: str | None = Field(default=None, max_length=64)
    # Day the user picked in the chat's date selector (past days only; None = today).
    log_date: date | None = None


class CancelIn(BaseModel):
    client_request_id: str = Field(min_length=1, max_length=64)


class ItemIn(BaseModel):
    """One food item as estimated by the LLM (also used to validate tool input)."""
    ingredient_name: str = Field(min_length=1, max_length=200)
    brand_name: str | None = None
    quantity: float = Field(gt=0)
    unit: str = Field(min_length=1, max_length=32)
    calories: float = Field(ge=0)
    protein_g: float = Field(ge=0)
    carbs_g: float = Field(ge=0)
    fat_g: float = Field(ge=0)
    fiber_g: float = Field(default=0, ge=0)
    # Library link: when set, nutrients are computed from the user's saved food/recipe.
    food_id: int | None = None
    # General-list link (services/general_foods.py): nutrients are computed from the list.
    general_id: str | None = Field(default=None, max_length=80)
    # Approximate grams in one unit, when the unit is a piece/serving/cup etc.
    unit_weight_g: float | None = Field(default=None, gt=0)
    # Estimated micronutrients for this amount ({"iron_mg": 1.2, ...}); unknown keys dropped.
    micronutrients: dict | None = None

    @field_validator("micronutrients", mode="before")
    @classmethod
    def clean_micros(cls, v):
        from app.services.micros import clean
        return clean(v) if isinstance(v, dict) else None
