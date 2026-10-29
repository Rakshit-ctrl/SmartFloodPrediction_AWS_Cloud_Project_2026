# Risk assessment methodology and alert triggers

## What the risk score is
`POST /api/risk-assessments` computes an **illustrative demo score** (method id `demo_heuristic_v1`).
It is stored with `method="demo_heuristic_v1"` and `validated=false`. It is **not** a validated flood
forecast and must not be used for emergency or operational decisions.

```
score = min(rainfall_mm / 150, 1) * 70  +  (0 if river_level_m is None else min(river_level_m / 8, 1) * 30)
score = round(min(score, 100), 1)
level = High if score >= 70, Moderate if score >= 35, otherwise Low
```

Inputs are user-entered. Limitations:
- `rainfall_mm` has no defined accumulation window; the caller chooses it. The 150 mm and 8 m saturation
  points and the 70/30 weights are arbitrary demo constants, not calibrated to any catchment.
- No terrain, soil saturation, drainage, tide, upstream flow, or satellite flood extent is used.
- The weather feed is **not** wired into the score. OpenWeather reports rain over the last 1 h or 3 h,
  which does not match the unspecified window the heuristic assumes; combining them would imply a
  precision the method does not have.

## What "validated" means here
`validated` stays `false` for every method until that method has documented evaluation on held-out,
event-separated data (see `docs/MODEL_INTEGRATION.md`). No method in this repository meets that bar today.
Satellite segmentation (flooded-pixel mapping) and weather observations are separate concepts and are
not combined into this score.

## Alert rules and the trigger condition
A rule has a name, a location string, a threshold (0 to 100 risk score) and an enabled flag.
When an assessment is created, each rule is evaluated **in the same database transaction**.
A rule triggers when all of these hold:

1. the rule is enabled;
2. the rule location equals the assessment location after trimming, collapsing spaces and case-folding
   (exact match, so "Chennai" does not match "Chennai, IN");
3. `assessment.risk_score >= rule.threshold` (the boundary is inclusive).

Each match is written to `alert_events` with `delivery_status="dry_run"`, a snapshot of the rule, and the
assessment's `method` and `validated` values. **Nothing is delivered.** Events are kept if the rule is
later edited or deleted.

## Gate for Amazon SNS (not implemented yet)
SNS delivery will be added only after this trigger condition is tested (done in `tests/test_risk_alerts.py`)
and will be disabled by default. It must refuse to publish for events where `validated` is `false`, so
demo scores can never produce a real notification.

## Known limitations
- No de-duplication or cooldown: every matching assessment writes its own event.
- Location matching is by string, not geography.
- Rules are global (no per-user ownership) until Cognito authentication is added.
