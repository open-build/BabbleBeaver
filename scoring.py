"""
Kai MAI Scoring Engine — deterministic implementation of SCORING.md.

Every rule in SCORING.md is implemented here as a pure function so the math is
exact, testable, and never delegated to the LLM. The orchestration layer
(`compute_scores`) pulls inputs from the same user_context dict produced by
user_context.fetch_user_context, computes foundation scores (Rules 1–10) before
composites (Rules 11–18), enforces CGM gating, and flags any score whose inputs
are missing rather than inventing data (GLOBAL HARD CONSTRAINT 1).

A score is represented as a ScoreResult: a numeric value in [0, 100] when all
required inputs are present, or value=None with complete=False otherwise.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Result type and numeric helpers
# ---------------------------------------------------------------------------


@dataclass
class ScoreResult:
    """A single rule's outcome. value is None when inputs are incomplete."""

    name: str
    value: Optional[float]
    complete: bool
    note: str = ""

    @property
    def display(self) -> str:
        if self.value is None:
            return f"{self.name}: n/a ({self.note or 'insufficient data'})"
        return f"{self.name}: {self.value:.0f}%"


def _clamp(score: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, score))


def _higher_is_better(actual: Optional[float], target: Optional[float]) -> Optional[float]:
    """Score = (Actual / Target) * 100, capped at 100 (RULE 0)."""
    if actual is None or target in (None, 0):
        return None
    return _clamp((actual / target) * 100.0)


def _lower_is_better(actual: Optional[float], target: Optional[float]) -> Optional[float]:
    """Score = 100 if Actual <= Target else (Target / Actual) * 100 (RULE 0)."""
    if actual is None or target in (None, 0):
        return None
    if actual <= target:
        return 100.0
    return _clamp((target / actual) * 100.0)


def _weighted(components: List[tuple[Optional[float], float]]) -> Optional[float]:
    """Weighted composite. Caps each subscore at 100 before weighting (CONSTRAINT 6).

    Returns None if any required component is missing — callers handle documented
    fallbacks (e.g. Rule 9 redistribution) before calling this.
    """
    total = 0.0
    for value, weight in components:
        if value is None:
            return None
        total += _clamp(value) * weight
    return _clamp(total)


# ---------------------------------------------------------------------------
# Typed inputs
# ---------------------------------------------------------------------------


@dataclass
class ScoringInputs:
    """All raw inputs the rules may consume. Every field is optional; missing
    inputs cause the dependent score to be flagged incomplete, never estimated."""

    # Scoring scope. "daily" applies SCORING.md targets verbatim. "meal" scales
    # daily intake targets down by meal_divisor so a single dish is judged against
    # a fair per-meal share (mirrors the spec's sodium 767mg = 2300÷3 fallback).
    # See "MEAL-LEVEL SCORING MODE" in SCORING.md.
    level: str = "daily"
    meal_divisor: float = 3.0

    # Demographics / profile
    sex: Optional[str] = None  # "male" / "female"
    body_weight_kg: Optional[float] = None

    # Nutrition intake (Rules 1–6)
    protein_g: Optional[float] = None
    fiber_g: Optional[float] = None
    calories_consumed: Optional[float] = None
    added_sugar_g: Optional[float] = None
    sat_fat_g: Optional[float] = None
    sodium_mg: Optional[float] = None
    sodium_meal_mg: Optional[float] = None

    # Calorie targets (Rule 3 / 5 / 6)
    provider_calorie_target: Optional[float] = None
    maintenance_calories: Optional[float] = None

    # Hydration (Rule 7)
    water_l: Optional[float] = None
    active_minutes: Optional[float] = None
    temperature_f: Optional[float] = None

    # Sleep (Rule 8)
    sleep_hours: Optional[float] = None
    sleep_efficiency_pct: Optional[float] = None
    sleep_timing_variation_min: Optional[float] = None
    sleep_debt_hours: Optional[float] = None

    # Activity (Rule 9)
    steps: Optional[float] = None
    weekly_exercise_sessions: Optional[float] = None
    current_activity_level: Optional[float] = None
    baseline_activity_level: Optional[float] = None

    # Glucose / CGM (Rule 10)
    cgm_connected: bool = False
    cgm_consent: bool = False
    tir_pct: Optional[float] = None
    glucose_cv_pct: Optional[float] = None
    post_meal_rise_mg: Optional[float] = None
    mean_glucose_mg: Optional[float] = None
    time_above_range_pct: Optional[float] = None

    # Externally-supplied subscores / signals used by composites (Rules 11–18).
    # These are not derivable from raw biometrics; supplied by the provider/app.
    glycemic_load_score: Optional[float] = None
    recovery_signal_score: Optional[float] = None
    nutrition_consistency_score: Optional[float] = None
    meal_timing_consistency_score: Optional[float] = None
    engagement_score: Optional[float] = None
    protocol_fit_score: Optional[float] = None
    body_state_fit_score: Optional[float] = None
    historical_response_fit_score: Optional[float] = None
    preference_fit_score: Optional[float] = None
    satiety_score: Optional[float] = None
    glucose_impact_score: Optional[float] = None
    energy_impact_score: Optional[float] = None
    recovery_support_score: Optional[float] = None

    # Behavioral drift (Rule 14): baseline vs current pairs.
    drift_nutrition: Optional[tuple[float, float]] = None  # (baseline, current)
    drift_activity: Optional[tuple[float, float]] = None
    drift_sleep: Optional[tuple[float, float]] = None
    drift_high_risk_meal: Optional[float] = None  # already-scored 0–100 increase
    drift_engagement: Optional[tuple[float, float]] = None
    drift_meal_timing_variability: Optional[float] = None  # already-scored 0–100

    # Recommendation confidence (Rule 18).
    nutrition_data_completeness: Optional[float] = None
    wearable_coverage: Optional[float] = None
    user_history_depth: Optional[float] = None
    similar_meal_evidence: Optional[float] = None
    past_prediction_accuracy: Optional[float] = None
    context_completeness: Optional[float] = None
    missing_data_penalty: float = 0.0


# ---------------------------------------------------------------------------
# Foundation scores (Rules 1–10)
# ---------------------------------------------------------------------------


def _meal_scale(i: ScoringInputs) -> float:
    """Divisor applied to daily targets when scoring a single meal (else 1)."""
    return i.meal_divisor if i.level == "meal" and i.meal_divisor else 1.0


def protein_adequacy(i: ScoringInputs) -> ScoreResult:
    if i.protein_g is None:
        return ScoreResult("Protein Adequacy", None, False, "no protein intake")
    target = 100.0
    if i.body_weight_kg:
        target = max(100.0, 1.2 * i.body_weight_kg)  # daily floor never below 100g
    target /= _meal_scale(i)  # meal mode scales the daily floor down
    return ScoreResult("Protein Adequacy", _higher_is_better(i.protein_g, target), True)


def fiber_adequacy(i: ScoringInputs) -> ScoreResult:
    if i.fiber_g is None:
        return ScoreResult("Fiber Adequacy", None, False, "no fiber intake")
    if i.calories_consumed:
        # Calorie-based target is already portion-proportional; no extra scaling.
        target = 14.0 * (i.calories_consumed / 1000.0)
    else:
        target = 30.0 / _meal_scale(i)  # default daily 30g, scaled for meal mode
    return ScoreResult("Fiber Adequacy", _higher_is_better(i.fiber_g, target), True)


def _calorie_target(i: ScoringInputs) -> Optional[float]:
    # Provider target overrides all (CONSTRAINT 8). Never mix provider + default.
    # A provider target is taken as-is (provider may set it per-meal); defaults
    # are daily and get scaled down in meal mode. Sugar/sat-fat targets derive
    # from this value, so they inherit the meal scaling automatically.
    if i.provider_calorie_target:
        return i.provider_calorie_target
    if i.maintenance_calories:
        return (i.maintenance_calories * 0.85) / _meal_scale(i)  # maintenance −15%
    if i.sex:
        base = 1600.0 if i.sex.lower().startswith("f") else 1900.0
        return base / _meal_scale(i)
    return None


def calorie_alignment(i: ScoringInputs) -> ScoreResult:
    target = _calorie_target(i)
    if i.calories_consumed is None or target in (None, 0):
        return ScoreResult("Calorie Alignment", None, False, "no calorie data/target")
    diff_pct = abs(i.calories_consumed - target) / target * 100.0
    return ScoreResult("Calorie Alignment", _clamp(100.0 - diff_pct), True)


def sodium_control(i: ScoringInputs) -> ScoreResult:
    if i.sodium_mg is not None:
        return ScoreResult("Sodium Control", _lower_is_better(i.sodium_mg, 2300.0), True)
    if i.sodium_meal_mg is not None:  # meal-level fallback only when daily absent
        return ScoreResult("Sodium Control", _lower_is_better(i.sodium_meal_mg, 767.0), True)
    return ScoreResult("Sodium Control", None, False, "no sodium data")


def added_sugar_control(i: ScoringInputs) -> ScoreResult:
    cal_target = _calorie_target(i)
    if i.added_sugar_g is None or cal_target in (None, 0):
        return ScoreResult("Added Sugar Control", None, False, "no sugar/calorie target")
    sugar_g_target = (cal_target * 0.10) / 4.0  # 4 cal/g, fixed
    return ScoreResult("Added Sugar Control", _lower_is_better(i.added_sugar_g, sugar_g_target), True)


def saturated_fat_control(i: ScoringInputs) -> ScoreResult:
    cal_target = _calorie_target(i)
    if i.sat_fat_g is None or cal_target in (None, 0):
        return ScoreResult("Saturated Fat Control", None, False, "no sat fat/calorie target")
    fat_g_target = (cal_target * 0.10) / 9.0  # 9 cal/g, fixed
    return ScoreResult("Saturated Fat Control", _lower_is_better(i.sat_fat_g, fat_g_target), True)


def hydration_alignment(i: ScoringInputs) -> ScoreResult:
    if i.water_l is None:
        return ScoreResult("Hydration Alignment", None, False, "no water intake")
    # Female default when sex unknown (conservative baseline).
    base = 3.7 if (i.sex and i.sex.lower().startswith("m")) else 2.7
    target = base
    if i.active_minutes:
        # +0.25L per 30 active minutes or fraction thereof (ceil).
        import math
        target += 0.25 * math.ceil(i.active_minutes / 30.0)
    if i.temperature_f is not None and i.temperature_f > 80:
        target += 0.5
    return ScoreResult("Hydration Alignment", _higher_is_better(i.water_l, target), True)


def sleep_quality(i: ScoringInputs) -> ScoreResult:
    # All four subscores required — do not skip and redistribute (constraint).
    if None in (
        i.sleep_hours,
        i.sleep_efficiency_pct,
        i.sleep_timing_variation_min,
        i.sleep_debt_hours,
    ):
        return ScoreResult("Sleep Quality", None, False, "incomplete sleep metrics")

    h = i.sleep_hours
    if 7 <= h <= 9:
        duration = 100.0
    elif h < 7:
        duration = _clamp((h / 7.0) * 100.0)
    else:
        duration = _clamp((9.0 / h) * 100.0)

    efficiency = _clamp((i.sleep_efficiency_pct / 85.0) * 100.0)  # target fixed 85%

    v = i.sleep_timing_variation_min
    consistency = 100.0 if v <= 60 else _clamp((60.0 / v) * 100.0)

    debt = 100.0 if i.sleep_debt_hours <= 0 else _clamp(100.0 - (i.sleep_debt_hours * 15.0))

    value = (duration * 0.35) + (efficiency * 0.30) + (consistency * 0.20) + (debt * 0.15)
    return ScoreResult("Sleep Quality", _clamp(value), True)


def _sleep_consistency_subscore(i: ScoringInputs) -> Optional[float]:
    v = i.sleep_timing_variation_min
    if v is None:
        return None
    return 100.0 if v <= 60 else _clamp((60.0 / v) * 100.0)


def activity_alignment(i: ScoringInputs) -> ScoreResult:
    steps = _higher_is_better(i.steps, 8000.0)
    active = _higher_is_better(i.active_minutes, 21.0)
    sessions = _higher_is_better(i.weekly_exercise_sessions, 2.0)

    if i.baseline_activity_level:
        baseline = _higher_is_better(i.current_activity_level, i.baseline_activity_level)
        value = _weighted(
            [(steps, 0.30), (active, 0.30), (sessions, 0.20), (baseline, 0.20)]
        )
    else:
        # Redistribute baseline's 20% across the other three (rule fallback).
        value = _weighted([(steps, 0.37), (active, 0.37), (sessions, 0.26)])

    if value is None:
        return ScoreResult("Activity Alignment", None, False, "incomplete activity metrics")
    return ScoreResult("Activity Alignment", value, True)


def glucose_stability(i: ScoringInputs) -> ScoreResult:
    # CGM gating is binary: connection AND consent both required (CONSTRAINT 3).
    if not (i.cgm_connected and i.cgm_consent):
        return ScoreResult("Glucose Stability", None, False, "CGM not connected/consented")
    if None in (
        i.tir_pct,
        i.glucose_cv_pct,
        i.post_meal_rise_mg,
        i.mean_glucose_mg,
        i.time_above_range_pct,
    ):
        return ScoreResult("Glucose Stability", None, False, "incomplete CGM metrics")

    tir = _clamp((i.tir_pct / 70.0) * 100.0)
    variability = 100.0 if i.glucose_cv_pct <= 36 else _clamp((36.0 / i.glucose_cv_pct) * 100.0)
    post_meal = 100.0 if i.post_meal_rise_mg <= 40 else _clamp((40.0 / i.post_meal_rise_mg) * 100.0)
    mean_glucose = _clamp(100.0 - (abs(i.mean_glucose_mg - 100.0) / 100.0 * 100.0))
    tar = 100.0 if i.time_above_range_pct <= 25 else _clamp((25.0 / i.time_above_range_pct) * 100.0)

    value = (tir * 0.35) + (variability * 0.25) + (post_meal * 0.20) + (mean_glucose * 0.10) + (tar * 0.10)
    return ScoreResult("Glucose Stability", _clamp(value), True)


# ---------------------------------------------------------------------------
# Composite scores (Rules 11–18)
# ---------------------------------------------------------------------------


def nutrition_quality(i: ScoringInputs, f: Dict[str, ScoreResult]) -> ScoreResult:
    value = _weighted(
        [
            (f["protein"].value, 0.25),
            (f["fiber"].value, 0.20),
            (f["calorie"].value, 0.15),
            (i.glycemic_load_score, 0.15),  # must be scored first (constraint)
            (f["added_sugar"].value, 0.10),
            (f["sat_fat"].value, 0.10),
            (f["sodium"].value, 0.05),
        ]
    )
    if value is None:
        return ScoreResult("Nutrition Quality", None, False, "missing component scores")
    return ScoreResult("Nutrition Quality", value, True)


def body_state(i: ScoringInputs, f: Dict[str, ScoreResult]) -> ScoreResult:
    # Determine CGM status FIRST, then lock the weight set (constraint).
    cgm = i.cgm_connected and i.cgm_consent
    if cgm:
        value = _weighted(
            [
                (f["sleep"].value, 0.25),
                (f["activity"].value, 0.20),
                (i.recovery_signal_score, 0.15),
                (i.nutrition_consistency_score, 0.15),
                (f["hydration"].value, 0.10),
                (f["glucose"].value, 0.15),
            ]
        )
    else:
        value = _weighted(
            [
                (f["sleep"].value, 0.29),
                (f["activity"].value, 0.24),
                (i.recovery_signal_score, 0.22),
                (i.nutrition_consistency_score, 0.20),
                (f["hydration"].value, 0.05),
            ]
        )
    if value is None:
        return ScoreResult("Body State", None, False, "missing component scores")
    return ScoreResult("Body State", value, True)


def glp1_protocol_alignment(i: ScoringInputs, f: Dict[str, ScoreResult]) -> ScoreResult:
    # Engagement defaults to 0 when unknown (constraint), never assumed 100.
    engagement = i.engagement_score if i.engagement_score is not None else 0.0
    value = _weighted(
        [
            (f["nutrition_quality"].value, 0.25),
            (f["protein"].value, 0.20),
            (f["activity"].value, 0.15),
            (f["hydration"].value, 0.10),
            (_sleep_consistency_subscore(i), 0.10),
            (i.meal_timing_consistency_score, 0.10),
            (engagement, 0.10),
        ]
    )
    if value is None:
        return ScoreResult("GLP-1 Protocol Alignment", None, False, "missing component scores")
    return ScoreResult("GLP-1 Protocol Alignment", value, True)


def _decline(pair: Optional[tuple[float, float]]) -> Optional[float]:
    """Decline score: ((baseline - current) / baseline) * 100, floored at 0."""
    if pair is None:
        return None
    baseline, current = pair
    if not baseline:
        return None
    return _clamp(((baseline - current) / baseline) * 100.0)


def behavioral_drift(i: ScoringInputs) -> ScoreResult:
    components = [
        (_decline(i.drift_nutrition), 0.25),
        (_decline(i.drift_activity), 0.20),
        (_decline(i.drift_sleep), 0.15),
        (i.drift_high_risk_meal, 0.15),
        (_decline(i.drift_engagement), 0.15),
        (i.drift_meal_timing_variability, 0.10),
    ]
    value = _weighted(components)
    if value is None:
        return ScoreResult("Behavioral Drift", None, False, "no baseline/drift data")
    band = "Low" if value <= 30 else "Moderate" if value <= 60 else "High"
    # NOTE: risk score — higher = worse. Not inverted here (constraint).
    return ScoreResult("Behavioral Drift", value, True, f"{band} Drift")


def meal_alignment(i: ScoringInputs, f: Dict[str, ScoreResult]) -> ScoreResult:
    # Historical response defaults to 50 (neutral) when unavailable (constraint).
    historical = i.historical_response_fit_score if i.historical_response_fit_score is not None else 50.0
    value = _weighted(
        [
            (f["nutrition_quality"].value, 0.35),
            (i.protocol_fit_score, 0.25),
            (i.body_state_fit_score, 0.15),
            (historical, 0.15),
            (i.preference_fit_score, 0.10),
        ]
    )
    if value is None:
        return ScoreResult("Meal Alignment", None, False, "missing component scores")
    return ScoreResult("Meal Alignment", value, True)


def predicted_meal_impact(i: ScoringInputs, f: Dict[str, ScoreResult]) -> ScoreResult:
    historical = i.historical_response_fit_score if i.historical_response_fit_score is not None else 50.0
    value = _weighted(
        [
            (f["meal_alignment"].value, 0.30),
            (i.satiety_score, 0.20),
            (i.glucose_impact_score, 0.20),
            (i.energy_impact_score, 0.15),
            (i.recovery_support_score, 0.10),
            (historical, 0.05),
        ]
    )
    if value is None:
        return ScoreResult("Predicted Meal Impact", None, False, "missing component scores")
    return ScoreResult("Predicted Meal Impact", value, True)


def overall_adherence(i: ScoringInputs, f: Dict[str, ScoreResult]) -> ScoreResult:
    drift = f["behavioral_drift"].value
    drift_control = None if drift is None else _clamp(100.0 - drift)  # invert (constraint)
    engagement = i.engagement_score if i.engagement_score is not None else 0.0
    cgm = i.cgm_connected and i.cgm_consent
    if cgm:
        value = _weighted(
            [
                (f["glp1"].value, 0.30),
                (f["nutrition_quality"].value, 0.20),
                (f["activity"].value, 0.15),
                (f["sleep"].value, 0.10),
                (engagement, 0.10),
                (f["glucose"].value, 0.10),
                (drift_control, 0.05),
            ]
        )
    else:
        value = _weighted(
            [
                (f["glp1"].value, 0.34),
                (f["nutrition_quality"].value, 0.24),
                (f["activity"].value, 0.17),
                (f["sleep"].value, 0.10),
                (engagement, 0.10),
                (drift_control, 0.05),
            ]
        )
    if value is None:
        return ScoreResult("Overall Adherence", None, False, "missing component scores")
    return ScoreResult("Overall Adherence", value, True)


def recommendation_confidence(i: ScoringInputs) -> ScoreResult:
    base = _weighted(
        [
            (i.nutrition_data_completeness, 0.25),
            (i.wearable_coverage, 0.20),
            (i.user_history_depth, 0.20),
            (i.similar_meal_evidence, 0.15),
            (i.past_prediction_accuracy, 0.10),
            (i.context_completeness, 0.10),
        ]
    )
    if base is None:
        return ScoreResult("Recommendation Confidence", None, False, "missing confidence inputs")
    # Penalty always applied, even if small (constraint); floor at 0.
    value = _clamp(base - i.missing_data_penalty)
    note = "LOW CONFIDENCE — data-quality warning" if value < 50 else ""
    return ScoreResult("Recommendation Confidence", value, True, note)


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------


def compute_scores(inputs: ScoringInputs) -> Dict[str, ScoreResult]:
    """Compute all rules in dependency order (foundation before composites)."""
    f: Dict[str, ScoreResult] = {}

    # Foundation (Rules 1–10)
    f["protein"] = protein_adequacy(inputs)
    f["fiber"] = fiber_adequacy(inputs)
    f["calorie"] = calorie_alignment(inputs)
    f["sodium"] = sodium_control(inputs)
    f["added_sugar"] = added_sugar_control(inputs)
    f["sat_fat"] = saturated_fat_control(inputs)
    f["hydration"] = hydration_alignment(inputs)
    f["sleep"] = sleep_quality(inputs)
    f["activity"] = activity_alignment(inputs)
    f["glucose"] = glucose_stability(inputs)

    # Composites (Rules 11–18) — order matters.
    f["nutrition_quality"] = nutrition_quality(inputs, f)
    f["body_state"] = body_state(inputs, f)
    f["glp1"] = glp1_protocol_alignment(inputs, f)
    f["behavioral_drift"] = behavioral_drift(inputs)
    f["meal_alignment"] = meal_alignment(inputs, f)
    f["predicted_meal_impact"] = predicted_meal_impact(inputs, f)
    f["overall_adherence"] = overall_adherence(inputs, f)
    f["recommendation_confidence"] = recommendation_confidence(inputs)
    return f


# ---------------------------------------------------------------------------
# Extraction layer — map a user_context dict to ScoringInputs
# ---------------------------------------------------------------------------

# Candidate biometric signal keys (case-insensitive) per input. user_service's
# /body-signals payload is keyed by signal name; we tolerate naming variants and
# leave the input None (→ incomplete score) when no candidate matches.
_SIGNAL_KEYS: Dict[str, List[str]] = {
    "protein_g": ["protein", "protein_g", "protein_consumed"],
    "fiber_g": ["fiber", "fiber_g", "dietary_fiber"],
    "calories_consumed": ["calories", "calories_consumed", "energy_intake", "kcal"],
    "added_sugar_g": ["added_sugar", "added_sugar_g", "sugar_added"],
    "sat_fat_g": ["saturated_fat", "sat_fat", "saturated_fat_g"],
    "sodium_mg": ["sodium", "sodium_mg"],
    "water_l": ["water", "water_l", "hydration", "water_intake"],
    "active_minutes": ["active_minutes", "active_min", "exercise_minutes"],
    "temperature_f": ["temperature", "temp_f", "ambient_temp"],
    "sleep_hours": ["sleep_hours", "sleep_duration", "sleep"],
    "sleep_efficiency_pct": ["sleep_efficiency", "sleep_efficiency_pct"],
    "sleep_timing_variation_min": ["sleep_timing_variation", "sleep_consistency_min"],
    "sleep_debt_hours": ["sleep_debt", "sleep_debt_hours"],
    "steps": ["steps", "step_count", "daily_steps"],
    "weekly_exercise_sessions": ["weekly_exercise_sessions", "exercise_sessions"],
    "current_activity_level": ["current_activity_level", "activity_level"],
    "baseline_activity_level": ["baseline_activity_level", "activity_baseline"],
    "tir_pct": ["time_in_range", "tir", "tir_pct"],
    "glucose_cv_pct": ["glucose_cv", "glucose_variability", "cv"],
    "post_meal_rise_mg": ["post_meal_rise", "glucose_excursion"],
    "mean_glucose_mg": ["mean_glucose", "average_glucose"],
    "time_above_range_pct": ["time_above_range", "tar", "tar_pct"],
    "body_weight_kg": ["weight", "body_weight", "weight_kg"],
}


def _lookup_signal(biometrics: Dict[str, Any], candidates: List[str]) -> Optional[float]:
    if not biometrics:
        return None
    lowered = {str(k).lower(): v for k, v in biometrics.items()}
    for cand in candidates:
        entry = lowered.get(cand)
        if entry is None:
            continue
        value = entry.get("value") if isinstance(entry, dict) else entry
        try:
            return float(value)
        except (TypeError, ValueError):
            continue
    return None


def inputs_from_context(ctx: Optional[Dict[str, Any]]) -> ScoringInputs:
    """Build ScoringInputs from a fetch_user_context() dict. Unmapped fields
    stay None so their scores are flagged incomplete rather than estimated."""
    inputs = ScoringInputs()
    if not ctx:
        return inputs

    profile = ctx.get("profile") or {}
    biometrics = ctx.get("biometrics") or {}
    providers = [str(p).lower() for p in (ctx.get("connected_providers") or [])]

    # Profile-derived
    sex = profile.get("sex") or profile.get("gender")
    if isinstance(sex, str) and sex.strip():
        inputs.sex = sex
    for wkey in ("body_weight_kg", "weight_kg", "weight"):
        if profile.get(wkey):
            try:
                inputs.body_weight_kg = float(profile[wkey])
                break
            except (TypeError, ValueError):
                pass

    # Biometric-derived
    for field_name, candidates in _SIGNAL_KEYS.items():
        if getattr(inputs, field_name) is not None:
            continue
        val = _lookup_signal(biometrics, candidates)
        if val is not None:
            setattr(inputs, field_name, val)

    # CGM gating: a connected CGM provider implies connection + consent (the
    # provider link is only created after the user consents in user_service).
    cgm = any("cgm" in p or "dexcom" in p or "libre" in p for p in providers)
    inputs.cgm_connected = cgm
    inputs.cgm_consent = cgm

    return inputs


# ---------------------------------------------------------------------------
# Prompt formatting
# ---------------------------------------------------------------------------

# Scores surfaced to Kai's prompt, in the order most useful for ranking meals.
# Composites lead (richest signal) but only appear when their inputs are complete;
# foundation scores follow so Kai still gets usable signal from biometrics alone.
_PROMPT_ORDER = [
    ("overall_adherence", "Overall Adherence"),
    ("body_state", "Body State"),
    ("nutrition_quality", "Nutrition Quality"),
    ("glp1", "GLP-1 Protocol Alignment"),
    ("behavioral_drift", "Behavioral Drift (risk: higher=worse)"),
    ("recommendation_confidence", "Recommendation Confidence"),
    ("protein", "Protein Adequacy"),
    ("fiber", "Fiber Adequacy"),
    ("calorie", "Calorie Alignment"),
    ("added_sugar", "Added Sugar Control"),
    ("sat_fat", "Saturated Fat Control"),
    ("sodium", "Sodium Control"),
    ("hydration", "Hydration Alignment"),
    ("sleep", "Sleep Quality"),
    ("activity", "Activity Alignment"),
    ("glucose", "Glucose Stability"),
]


def format_scores_block(scores: Dict[str, ScoreResult]) -> str:
    """Render computed scores for prompt injection. Empty string if none are
    complete — the block is only added when there's real signal."""
    lines: List[str] = []
    for key, label in _PROMPT_ORDER:
        result = scores.get(key)
        if result and result.complete and result.value is not None:
            suffix = f" — {result.note}" if result.note else ""
            lines.append(f"- {label}: {result.value:.0f}%{suffix}")
    if not lines:
        return ""
    header = (
        "KAI HEALTH SCORES (0–100, computed from the user's data; higher is better "
        "except where noted). Use these to weight and justify recommendations — "
        "favor meals that support low scores. Do not recite the numbers verbatim."
    )
    return header + "\n" + "\n".join(lines)


def score_context(ctx: Optional[Dict[str, Any]]) -> str:
    """Convenience: context dict → prompt-ready score block."""
    return format_scores_block(compute_scores(inputs_from_context(ctx)))


# ---------------------------------------------------------------------------
# Serialization (for persistence)
# ---------------------------------------------------------------------------


def serialize_scores(scores: Dict[str, ScoreResult]) -> Dict[str, Any]:
    """Flatten ScoreResults to a JSON-safe dict for storage."""
    return {
        key: {"name": r.name, "value": r.value, "complete": r.complete, "note": r.note}
        for key, r in scores.items()
    }


def deserialize_scores(data: Dict[str, Any]) -> Dict[str, ScoreResult]:
    """Rebuild ScoreResults from stored JSON (inverse of serialize_scores)."""
    return {
        key: ScoreResult(
            name=d.get("name", key),
            value=d.get("value"),
            complete=d.get("complete", False),
            note=d.get("note", ""),
        )
        for key, d in (data or {}).items()
    }
