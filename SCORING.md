# KAI MAI SCORING SYSTEM — HARD RULES

These rules are authoritative. When computing any Kai score, follow them exactly. Do not infer, approximate, or substitute values unless a rule explicitly permits a fallback.

---

## RULE 0 — UNIVERSAL SCORE CONSTRAINTS

- All scores output a value between **0 and 100**, inclusive.
- Never return a score below 0 or above 100.
- Scores are expressed as a **percentage (%)**.
- Round final scores to the nearest whole number unless instructed otherwise.
- Two formula types exist:
  - **Higher is better:** `Score = (Actual ÷ Target) × 100`, capped at 100.
  - **Lower is better:** `Score = (Target ÷ Actual) × 100`, capped at 100. If Actual ≤ Target, score = 100.

---

## RULE 1 — PROTEIN ADEQUACY SCORE
**Type:** Higher is better.

**Target (use the higher of the two):**
- 100g protein/day
- 1.2g × user body weight in kg

**Formula:**
```
Score = (Actual protein consumed ÷ Protein target) × 100
```

**Hard constraints:**
- NEVER use a target below 100g, even for very light users.
- If body weight is unknown, use 100g as the default target.
- Cap at 100. Do not reward exceeding the target.

---

## RULE 2 — FIBER ADEQUACY SCORE
**Type:** Higher is better.

**Target (use one of the following, in order of availability):**
1. 30g/day (default)
2. 14g per 1,000 calories consumed (calorie-based alternative)

**Formula:**
```
Score = (Actual fiber consumed ÷ Fiber target) × 100
```

**Hard constraints:**
- Default to 30g/day unless calorie data is available and the calorie-based target is preferred.
- Cap at 100.

---

## RULE 3 — CALORIE ALIGNMENT SCORE
**Type:** Proximity to target (not higher-is-better or lower-is-better).

**Target (use in order of availability):**
1. Provider-set calorie target
2. User maintenance calories minus 15%
3. Female default: 1,600 cal/day
4. Male default: 1,900 cal/day

**Formula:**
```
Difference% = |Actual calories - Target calories| ÷ Target calories × 100
Score = 100 - Difference%
```

**Hard constraints:**
- Use absolute value — being over OR under the target both reduce the score equally.
- Cap at 100, floor at 0.
- Never use a provider target and a default target simultaneously.

---

## RULE 4 — SODIUM CONTROL SCORE
**Type:** Lower is better.

**Target:** 2,300mg/day  
**Meal-level fallback:** 767mg/meal (2,300 ÷ 3)

**Formula:**
```
If Actual ≤ 2,300mg: Score = 100
If Actual > 2,300mg: Score = (2,300 ÷ Actual) × 100
```

**Hard constraints:**
- Never penalize sodium under the target.
- Use daily total when available; use meal-level fallback only when daily total is unavailable.

---

## RULE 5 — ADDED SUGAR CONTROL SCORE
**Type:** Lower is better.

**Target calculation:**
```
Sugar calorie target = Daily calorie target × 10%
Sugar gram target = Sugar calorie target ÷ 4
```

**Formula:**
```
If Actual added sugar ≤ Sugar gram target: Score = 100
If Actual added sugar > Sugar gram target: Score = (Sugar gram target ÷ Actual added sugar) × 100
```

**Hard constraints:**
- Always derive the gram target from the calorie target — do not use a fixed gram default.
- Use 4 cal/gram as the conversion factor for sugar. Never change this.
- Never penalize sugar intake under the target.

---

## RULE 6 — SATURATED FAT CONTROL SCORE
**Type:** Lower is better.

**Target calculation:**
```
Sat fat calorie target = Daily calorie target × 10%
Sat fat gram target = Sat fat calorie target ÷ 9
```

**Formula:**
```
If Actual sat fat ≤ Sat fat gram target: Score = 100
If Actual sat fat > Sat fat gram target: Score = (Sat fat gram target ÷ Actual sat fat) × 100
```

**Hard constraints:**
- Always derive the gram target from the calorie target — do not use a fixed gram default.
- Use 9 cal/gram as the conversion factor for fat. Never change this.
- Never penalize sat fat intake under the target.

---

## RULE 7 — HYDRATION ALIGNMENT SCORE
**Type:** Higher is better.

**Base targets:**
- Female: 2.7 liters/day
- Male: 3.7 liters/day

**Adjustments (additive):**
- +0.25L per 30 active minutes (or fraction thereof)
- +0.5L if temperature > 80°F

**Formula:**
```
Final target = Base target + activity adjustment + heat adjustment
Score = (Actual water intake ÷ Final target) × 100
```

**Hard constraints:**
- Always apply adjustments before computing the score — never score against the unadjusted base target when adjustment data is available.
- Cap at 100.
- If sex is unknown, use female default (2.7L) as the conservative baseline.

---

## RULE 8 — SLEEP QUALITY SCORE
**Type:** Weighted composite. Higher is better.

**Weights:**
- Sleep Duration: 35%
- Sleep Efficiency: 30%
- Sleep Consistency: 20%
- Sleep Debt: 15%

**Subscore formulas:**

**Duration:**
```
If 7–9 hours: 100
If < 7 hours: (Actual hours ÷ 7) × 100
If > 9 hours: (9 ÷ Actual hours) × 100
```

**Efficiency:**
```
Score = (Actual efficiency% ÷ 85) × 100
```

**Consistency:**
```
If timing varies ≤ 60 min: 100
If timing varies > 60 min: (60 ÷ Actual variation in minutes) × 100
```

**Sleep Debt:**
```
If no debt: 100
If debt exists: 100 - (Debt hours × 15)
Floor at 0.
```

**Final formula:**
```
Sleep Quality = (Duration × 0.35) + (Efficiency × 0.30) + (Consistency × 0.20) + (Debt × 0.15)
```

**Hard constraints:**
- All four subscores must be computed. Do not skip a subscore and redistribute weights.
- Sleep Debt subscore floors at 0 — never go negative.
- Efficiency target is fixed at 85%. Do not adjust.

---

## RULE 9 — ACTIVITY ALIGNMENT SCORE
**Type:** Weighted composite. Higher is better.

**Weights:**
- Step Target: 30%
- Active Minutes: 30%
- Exercise Consistency: 20%
- Baseline Improvement: 20%

**Targets:**
- Steps: 8,000/day
- Active minutes: 21/day (150 ÷ 7)
- Exercise sessions: 2/week

**Subscore formulas:**
```
Steps Score = (Actual steps ÷ 8,000) × 100
Active Minutes Score = (Actual active minutes ÷ 21) × 100
Exercise Consistency Score = (Actual weekly sessions ÷ 2) × 100
Baseline Improvement Score = (Current activity level ÷ Baseline activity level) × 100
```

**Final formula:**
```
Activity Alignment = (Steps × 0.30) + (Active Minutes × 0.30) + (Exercise Consistency × 0.20) + (Baseline Improvement × 0.20)
```

**Hard constraints:**
- Cap all subscores at 100 before applying weights.
- If baseline activity is unavailable, exclude Baseline Improvement and redistribute its 20% weight equally across the other three components (Steps: 37%, Active Minutes: 37%, Exercise Consistency: 26% — approximate).
- Step target is fixed at 8,000. Do not change without explicit provider override.

---

## RULE 10 — GLUCOSE STABILITY SCORE
**Type:** Weighted composite. Higher is better.  
**Activation requirement:** CGM must be connected AND user consent must be active. Never compute without both.

**Weights:**
- Time in Range: 35%
- Variability Control: 25%
- Post-Meal Excursion Control: 20%
- Mean Glucose Alignment: 10%
- Time Above Range Control: 10%

**Targets:**
- Time in range (TIR): ≥70% (range: 70–180 mg/dL)
- Glucose variability (CV): <36%
- Post-meal glucose rise: <40 mg/dL
- Mean glucose: 100 mg/dL
- Time above range: <25%

**Subscore formulas:**
```
TIR Score = (Actual TIR% ÷ 70) × 100

Variability Score = (36 ÷ Actual CV%) × 100
  → If Actual CV% ≤ 36: Score = 100

Post-Meal Score = (40 ÷ Actual post-meal rise) × 100
  → If Actual rise ≤ 40: Score = 100

Mean Glucose Score = 100 - (|Actual mean - 100| ÷ 100 × 100)

Time Above Range Score = (25 ÷ Actual time above range%) × 100
  → If Actual time above range ≤ 25%: Score = 100
```

**Final formula:**
```
Glucose Stability = (TIR × 0.35) + (Variability × 0.25) + (Post-Meal × 0.20) + (Mean Glucose × 0.10) + (Time Above Range × 0.10)
```

**Hard constraints:**
- Do not compute or display this score without confirmed CGM connection and active consent.
- All subscore caps at 100.

---

## RULE 11 — NUTRITION QUALITY SCORE
**Type:** Weighted composite. Higher is better.

**Weights:**
- Protein Adequacy: 25%
- Fiber Adequacy: 20%
- Calorie Alignment: 15%
- Glycemic Load Control: 15%
- Added Sugar Control: 10%
- Saturated Fat Control: 10%
- Sodium Control: 5%

**Formula:**
```
Nutrition Quality = (Protein × 0.25) + (Fiber × 0.20) + (Calorie × 0.15) + (Glycemic Load × 0.15) + (Added Sugar × 0.10) + (Sat Fat × 0.10) + (Sodium × 0.05)
```

**Hard constraints:**
- All component scores must come from their respective scored metrics (Rules 1–6).
- Weights must sum to 1.00. Do not adjust weights.
- Glycemic Load Control must be scored before this composite can be computed.

---

## RULE 12 — BODY STATE SCORE
**Type:** Weighted composite. Higher is better.  
**Two versions — CGM and non-CGM. Never mix weights between versions.**

**With CGM:**
- Sleep Quality: 25%
- Activity Alignment: 20%
- Recovery Signal: 15%
- Nutrition Consistency: 15%
- Hydration Alignment: 10%
- Glucose Stability: 15%

```
Body State = (Sleep × 0.25) + (Activity × 0.20) + (Recovery × 0.15) + (Nutrition Consistency × 0.15) + (Hydration × 0.10) + (Glucose × 0.15)
```

**Without CGM:**
- Sleep Quality: 29%
- Activity Alignment: 24%
- Recovery Signal: 22%
- Nutrition Consistency: 20%
- Hydration Alignment: 5%

```
Body State = (Sleep × 0.29) + (Activity × 0.24) + (Recovery × 0.22) + (Nutrition Consistency × 0.20) + (Hydration × 0.05)
```

**Hard constraints:**
- Determine CGM status FIRST. Then lock in the correct weight set.
- Do not use CGM weights if CGM is disconnected mid-session.

---

## RULE 13 — GLP-1 PROTOCOL ALIGNMENT SCORE
**Type:** Weighted composite. Higher is better.

**Weights:**
- Nutrition Alignment: 25%
- Protein Target Adherence: 20%
- Activity Alignment: 15%
- Hydration Alignment: 10%
- Sleep Consistency: 10%
- Meal Timing Consistency: 10%
- Engagement: 10%

**Formula:**
```
GLP-1 Protocol Alignment = (Nutrition × 0.25) + (Protein × 0.20) + (Activity × 0.15) + (Hydration × 0.10) + (Sleep Consistency × 0.10) + (Meal Timing × 0.10) + (Engagement × 0.10)
```

**Hard constraints:**
- Weights sum to 1.00. Do not redistribute.
- "Engagement" is a tracked behavioral signal — do not assume 100 if unknown. Default to 0 if no engagement data exists.

---

## RULE 14 — BEHAVIORAL DRIFT SCORE
**Type:** Risk score. Higher = more risk.  
**Interpretation is INVERTED from all other scores.**

**Baseline:**
- Use rolling 14-day or 30-day average.
- If no baseline exists, use first 7 days of data as baseline.
- Never score drift without a baseline.

**Weights:**
- Nutrition Decline: 25%
- Activity Decline: 20%
- Sleep Decline: 15%
- High-Risk Meal Increase: 15%
- Engagement Decline: 15%
- Meal Timing Variability: 10%

**Subscore formula (decline metrics):**
```
Decline Score = ((Baseline value - Current value) ÷ Baseline value) × 100
Floor at 0 — improvement does not generate negative drift.
```

**Final formula:**
```
Behavioral Drift = (Nutrition Decline × 0.25) + (Activity Decline × 0.20) + (Sleep Decline × 0.15) + (High-Risk Meal × 0.15) + (Engagement Decline × 0.15) + (Meal Timing Variability × 0.10)
```

**Interpretation bands:**
- 0–30: Low Drift
- 31–60: Moderate Drift
- 61–100: High Drift

**Hard constraints:**
- Do NOT invert this score before display. It is intentionally a risk-increasing metric.
- When used in Overall Adherence (Rule 17), it IS inverted: `Drift Control = 100 - Behavioral Drift`.
- Decline subscores floor at 0. Improvement in a metric does not pull drift negative.

---

## RULE 15 — MEAL ALIGNMENT SCORE
**Type:** Weighted composite. Higher is better.

**Weights:**
- Nutrition Quality: 35%
- Protocol Fit: 25%
- Current Body State Fit: 15%
- Historical Response Fit: 15%
- Preference Fit: 10%

**Formula:**
```
Meal Alignment = (Nutrition Quality × 0.35) + (Protocol Fit × 0.25) + (Body State Fit × 0.15) + (Historical Response × 0.15) + (Preference Fit × 0.10)
```

**Hard constraints:**
- Nutrition Quality must be scored per Rule 11 before this composite can be computed.
- If historical data is unavailable, set Historical Response Fit to 50 (neutral) rather than 0.

---

## RULE 16 — PREDICTED MEAL IMPACT SCORE
**Type:** Weighted composite. Higher is better.

**Weights:**
- Meal Alignment: 30%
- Satiety Potential: 20%
- Glucose Stability Impact: 20%
- Energy Stability Impact: 15%
- Recovery Support: 10%
- Historical Response Fit: 5%

**Formula:**
```
Predicted Meal Impact = (Meal Alignment × 0.30) + (Satiety × 0.20) + (Glucose Impact × 0.20) + (Energy Impact × 0.15) + (Recovery × 0.10) + (Historical Response × 0.05)
```

**Hard constraints:**
- Meal Alignment (Rule 15) must be computed first.
- If no CGM is connected, Glucose Stability Impact must be estimated from meal composition data only — flag the output as estimated.

---

## RULE 17 — OVERALL ADHERENCE SCORE
**Type:** Weighted composite. Higher is better.  
**Two versions — CGM and non-CGM. Never mix weights between versions.**

**Drift Control derivation (applies to both versions):**
```
Drift Control = 100 - Behavioral Drift Score
```

**With CGM:**
- GLP-1 Protocol Alignment: 30%
- Nutrition Quality: 20%
- Activity Alignment: 15%
- Sleep Quality: 10%
- Engagement: 10%
- Glucose Stability: 10%
- Drift Control: 5%

```
Overall Adherence = (GLP-1 × 0.30) + (Nutrition × 0.20) + (Activity × 0.15) + (Sleep × 0.10) + (Engagement × 0.10) + (Glucose × 0.10) + (Drift Control × 0.05)
```

**Without CGM:**
- GLP-1 Protocol Alignment: 34%
- Nutrition Quality: 24%
- Activity Alignment: 17%
- Sleep Quality: 10%
- Engagement: 10%
- Drift Control: 5%

```
Overall Adherence = (GLP-1 × 0.34) + (Nutrition × 0.24) + (Activity × 0.17) + (Sleep × 0.10) + (Engagement × 0.10) + (Drift Control × 0.05)
```

**Hard constraints:**
- Always invert Behavioral Drift to Drift Control before applying weight. Never use raw Behavioral Drift score here.
- CGM status must be determined before selecting weight set.

---

## RULE 18 — RECOMMENDATION CONFIDENCE SCORE
**Type:** Weighted composite, with penalty deduction. Higher is better.

**Weights:**
- Nutrition Data Completeness: 25%
- Wearable Coverage: 20%
- User History Depth: 20%
- Similar Meal Evidence: 15%
- Past Prediction Accuracy: 10%
- Context Completeness: 10%

**Formula:**
```
Base Score = (Nutrition Data × 0.25) + (Wearable Coverage × 0.20) + (User History × 0.20) + (Similar Meal Evidence × 0.15) + (Past Accuracy × 0.10) + (Context × 0.10)
Final Score = Base Score - Missing Data Penalty
```

**Hard constraints:**
- Missing Data Penalty must be explicitly calculated and applied — do not omit it even if small.
- Floor the final score at 0.
- This score gates recommendation delivery: low confidence scores should trigger a data-quality warning alongside the recommendation.

---

## GLOBAL HARD CONSTRAINTS (apply to all rules)

1. **Never invent data.** If an input value is missing, apply the documented default or flag the score as incomplete. Do not estimate inputs.
2. **Weights are fixed.** Do not redistribute component weights unless a rule explicitly provides a fallback redistribution.
3. **CGM gating is binary.** Either CGM is connected with active consent, or it is not. There is no partial CGM state.
4. **Scores are unitless percentages.** Never append units (mg, g, L) to a final score output.
5. **Score computation order matters.** Foundation scores (Rules 1–10) must be computed before composite scores (Rules 11–18) that depend on them.
6. **Cap before weighting.** In all weighted composites, cap each subscore at 100 before multiplying by its weight.
7. **Behavioral Drift is the only score where higher = worse.** In all other contexts, higher is better.
8. **Provider targets override all defaults.** If a provider has set a specific target for a metric, use it. Never silently fall back to a default when a provider target exists.

---

## MEAL-LEVEL SCORING MODE (extension)

All rules above define **daily** targets. When scoring a **single meal** (e.g. ranking dinner options), the engine supports an opt-in `level = "meal"` mode that scales daily intake targets down by a `meal_divisor` (default 3, mirroring the Rule 4 sodium fallback `767mg = 2300 ÷ 3`).

**Scaling in meal mode:**
- **Protein (Rule 1):** daily target (floor 100g, or `1.2 × kg`) ÷ divisor. *This intentionally relaxes the "never below 100g" daily floor — that floor is a daily constraint and would unfairly penalize any single meal.*
- **Fiber (Rule 2):** default 30g ÷ divisor. The calorie-based alternative is already portion-proportional and is not scaled.
- **Calorie / Added Sugar / Saturated Fat (Rules 3, 5, 6):** the default/maintenance calorie target ÷ divisor; sugar and sat-fat gram targets derive from it and scale automatically. A **provider-set** calorie target is used as-is (assumed already per-meal when in meal mode).
- **Sodium (Rule 4):** unchanged — already has the 767mg/meal fallback.

**Constraint:** Daily mode (`level = "daily"`) remains the default and applies Rules 1–18 verbatim. Meal mode is only for per-meal/per-dish comparisons and must never be used to report a user's daily adherence.