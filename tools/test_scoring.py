#!/usr/bin/env python3
"""
Unit tests for the Kai MAI scoring engine (scoring.py).

Pure math — no network. Run: python3 tools/test_scoring.py
Verifies formula correctness, caps/floors, CGM gating, and missing-data flagging
against the hard rules in SCORING.md.
"""

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from scoring import (  # noqa: E402
    ScoringInputs,
    compute_scores,
    inputs_from_context,
    protein_adequacy,
    fiber_adequacy,
    calorie_alignment,
    sodium_control,
    added_sugar_control,
    saturated_fat_control,
    hydration_alignment,
    sleep_quality,
    activity_alignment,
    glucose_stability,
    behavioral_drift,
    recommendation_confidence,
)

_passed = 0
_failed = 0


def check(label, got, expected, tol=0.5):
    global _passed, _failed
    if expected is None:
        ok = got is None
    elif got is None:
        ok = False
    else:
        ok = abs(got - expected) <= tol
    if ok:
        _passed += 1
        print(f"  PASS  {label}  (got {got})")
    else:
        _failed += 1
        print(f"  FAIL  {label}  expected {expected}, got {got}")


def main():
    global _passed, _failed
    # RULE 1 — protein: target = max(100, 1.2*kg). 90/120 -> 75.
    check("protein 90g @ 100kg", protein_adequacy(ScoringInputs(protein_g=90, body_weight_kg=100)).value, 75)
    # Cap at 100, light user never below 100g target.
    check("protein cap", protein_adequacy(ScoringInputs(protein_g=200, body_weight_kg=50)).value, 100)
    check("protein missing", protein_adequacy(ScoringInputs()).value, None)

    # RULE 2 — fiber default 30g. 15/30 -> 50.
    check("fiber 15g", fiber_adequacy(ScoringInputs(fiber_g=15)).value, 50)
    # Calorie-based: 14g/1000cal at 2000cal -> target 28; 28/28 -> 100.
    check("fiber cal-based", fiber_adequacy(ScoringInputs(fiber_g=28, calories_consumed=2000)).value, 100)

    # RULE 3 — calorie alignment proximity. female default 1600; 1440 -> diff 10% -> 90.
    check("calorie align", calorie_alignment(ScoringInputs(calories_consumed=1440, sex="female")).value, 90)
    # Over and under penalize equally.
    check("calorie over", calorie_alignment(ScoringInputs(calories_consumed=1760, sex="female")).value, 90)
    # Provider target overrides default.
    check("calorie provider", calorie_alignment(ScoringInputs(calories_consumed=2000, sex="female", provider_calorie_target=2000)).value, 100)

    # RULE 4 — sodium lower-is-better. Under target -> 100. 4600 -> 50.
    check("sodium under", sodium_control(ScoringInputs(sodium_mg=2000)).value, 100)
    check("sodium over", sodium_control(ScoringInputs(sodium_mg=4600)).value, 50)
    # Meal-level fallback only when daily absent (767mg target).
    check("sodium meal fallback", sodium_control(ScoringInputs(sodium_meal_mg=767)).value, 100)

    # RULE 5 — sugar target = (cal*10%)/4. 1600cal -> 40g target. 80g -> 50.
    check("sugar control", added_sugar_control(ScoringInputs(added_sugar_g=80, sex="female")).value, 50)

    # RULE 6 — sat fat target = (cal*10%)/9. Male default 1900cal -> 21.11g. 40g -> 52.78.
    check("sat fat control", saturated_fat_control(ScoringInputs(sat_fat_g=40, sex="male")).value, 52.78)

    # RULE 7 — hydration. male base 3.7 + 30min activity (0.25) + heat (0.5) = 4.45; 4.45 -> 100.
    check("hydration adjusted", hydration_alignment(ScoringInputs(water_l=4.45, sex="male", active_minutes=30, temperature_f=85)).value, 100)
    # Unknown sex -> female base 2.7. 1.35 -> 50.
    check("hydration default sex", hydration_alignment(ScoringInputs(water_l=1.35)).value, 50)

    # RULE 8 — sleep composite. Perfect inputs -> 100.
    perfect_sleep = ScoringInputs(sleep_hours=8, sleep_efficiency_pct=85, sleep_timing_variation_min=30, sleep_debt_hours=0)
    check("sleep perfect", sleep_quality(perfect_sleep).value, 100)
    # Missing one subscore -> incomplete (no redistribution).
    check("sleep incomplete", sleep_quality(ScoringInputs(sleep_hours=8, sleep_efficiency_pct=85)).value, None)
    # Sleep debt floors at 0: 8h debt -> debt subscore 0.
    debt_sleep = ScoringInputs(sleep_hours=8, sleep_efficiency_pct=85, sleep_timing_variation_min=30, sleep_debt_hours=8)
    # duration100*.35 + eff100*.30 + cons100*.20 + debt0*.15 = 85.
    check("sleep debt floor", sleep_quality(debt_sleep).value, 85)

    # RULE 9 — activity with baseline missing -> redistribute weights, still scores.
    act = activity_alignment(ScoringInputs(steps=8000, active_minutes=21, weekly_exercise_sessions=2))
    check("activity no baseline", act.value, 100)

    # RULE 10 — glucose gated: no CGM -> incomplete.
    check("glucose gated off", glucose_stability(ScoringInputs(tir_pct=80)).value, None)
    # Perfect with CGM connected+consented -> 100.
    g = ScoringInputs(cgm_connected=True, cgm_consent=True, tir_pct=70, glucose_cv_pct=36, post_meal_rise_mg=40, mean_glucose_mg=100, time_above_range_pct=25)
    check("glucose perfect", glucose_stability(g).value, 100)

    # RULE 14 — behavioral drift: nutrition declines 100->50 = 50% decline.
    drift = behavioral_drift(ScoringInputs(
        drift_nutrition=(100, 50), drift_activity=(100, 100), drift_sleep=(100, 100),
        drift_high_risk_meal=0, drift_engagement=(100, 100), drift_meal_timing_variability=0,
    ))
    # 50*.25 = 12.5 -> Low Drift band.
    check("behavioral drift", drift.value, 12.5)
    assert "Low" in drift.note, "drift band note"

    # RULE 18 — confidence with penalty applied and floored.
    conf = recommendation_confidence(ScoringInputs(
        nutrition_data_completeness=100, wearable_coverage=100, user_history_depth=100,
        similar_meal_evidence=100, past_prediction_accuracy=100, context_completeness=100,
        missing_data_penalty=10,
    ))
    check("confidence w/ penalty", conf.value, 90)

    # MEAL-LEVEL MODE — daily targets scaled by meal_divisor (default 3).
    # Protein: daily floor 100 / 3 = 33.3 target; 42g meal -> capped 100.
    check("meal protein", protein_adequacy(ScoringInputs(level="meal", protein_g=42)).value, 100)
    # Same 42g in daily mode scores against 100g floor -> 42.
    check("daily protein", protein_adequacy(ScoringInputs(level="daily", protein_g=42)).value, 42)
    # Fiber default 30/3 = 10 target; 10g meal -> 100.
    check("meal fiber", fiber_adequacy(ScoringInputs(level="meal", fiber_g=10)).value, 100)
    # Calorie female default 1600/3 = 533 target; 533cal meal -> 100.
    check("meal calorie", calorie_alignment(ScoringInputs(level="meal", sex="female", calories_consumed=533)).value, 100)
    # Provider target taken as-is even in meal mode (assumed per-meal).
    check("meal provider as-is", calorie_alignment(ScoringInputs(level="meal", sex="female", calories_consumed=500, provider_calorie_target=500)).value, 100)

    # Extraction layer: maps biometric signal keys, leaves unknowns None.
    ctx = {
        "profile": {"sex": "female", "weight_kg": 70},
        "biometrics": {
            "protein": {"value": 84, "unit": "g"},
            "Steps": {"value": 8000},
        },
        "connected_providers": ["dexcom_cgm"],
    }
    extracted = inputs_from_context(ctx)
    check("extract protein", extracted.protein_g, 84)
    check("extract steps (case-insensitive)", extracted.steps, 8000)
    assert extracted.cgm_connected and extracted.cgm_consent, "CGM provider implies consent"
    assert extracted.fiber_g is None, "unmapped input stays None"

    # Full pipeline runs without raising; foundation feeds composites.
    scores = compute_scores(extracted)
    assert "overall_adherence" in scores, "composite present"
    # target = max(100, 1.2*70=84) = 100 (floor); 84/100 -> 84.
    check("protein via pipeline", scores["protein"].value, 84)

    # Serialize round-trip preserves values and rebuilds the same prompt block.
    from scoring import serialize_scores, deserialize_scores, format_scores_block
    payload = serialize_scores(scores)
    assert isinstance(payload["protein"]["value"], float), "serialized value is JSON-safe"
    rebuilt = deserialize_scores(payload)
    assert format_scores_block(rebuilt) == format_scores_block(scores), "round-trip block matches"
    _passed += 1
    print("  PASS  serialize round-trip")

    print(f"\n{_passed} passed, {_failed} failed")
    sys.exit(1 if _failed else 0)


if __name__ == "__main__":
    main()
