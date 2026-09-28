"""Advanced analysis: per-day series, adherence and averages."""
from datetime import timedelta

from app.services.analysis import on_target
from tests.test_foods import CHICKEN, log_and_confirm


def test_on_target_rule():
    t = {"calories": 2000, "protein_g": 150}
    assert on_target({"calories": 2100, "protein_g": 140}, t) is True
    assert on_target({"calories": 2300, "protein_g": 150}, t) is False       # kcal off by 15%
    assert on_target({"calories": 2000, "protein_g": 120}, t) is False       # protein < 90%
    assert on_target({"calories": 2000, "protein_g": 150}, None) is None


def test_range_has_every_day_and_averages_logged_days_only(client, user, fake_llm):
    log_and_confirm(client, fake_llm, [CHICKEN])
    client.post("/api/water", json={"amount_ml": 750})
    r = client.get("/api/dashboard/range?days=7").json()
    assert len(r["days"]) == 7
    today = r["days"][-1]
    assert today["logged"] and today["calories"] == 165 and today["water_ml"] == 750
    assert today["on_target"] is False
    assert all(not d["logged"] and d["on_target"] is None for d in r["days"][:-1])
    s = r["summary"]
    assert (s["days_logged"], s["days_on_target"]) == (1, 0)
    assert s["avg"]["calories"] == 165 and s["avg"]["water_ml"] == 750
    assert round(sum(s["macro_split_pct"].values())) == 100
    assert r["water_target_ml"] == 80 * 35 + 500


def test_range_is_clamped(client, user):
    assert len(client.get("/api/dashboard/range?days=500").json()["days"]) == 90
