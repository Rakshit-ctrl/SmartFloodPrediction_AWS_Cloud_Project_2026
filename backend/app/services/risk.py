"""Demonstration risk heuristic (method id: demo_heuristic_v1).

NOT a validated flood forecast. See docs/RISK_METHODOLOGY.md.
Inputs: rainfall_mm (accumulation window chosen by the caller; saturates at 150 mm) and an
optional river level in metres (saturates at 8 m, not station-specific).
"""
from dataclasses import dataclass

METHOD_ID = "demo_heuristic_v1"
VALIDATED = False  # flips only when a method has documented held-out evaluation
EXPLANATION = "Demo heuristic only; not a validated flood forecast."


@dataclass(frozen=True)
class RiskResult:
    score: float
    level: str
    explanation: str
    method: str
    validated: bool


def assess(rain: float, river: float | None) -> RiskResult:
    score = min(rain / 150, 1) * 70 + (0 if river is None else min(river / 8, 1) * 30)
    score = round(min(score, 100), 1)
    level = "High" if score >= 70 else "Moderate" if score >= 35 else "Low"
    return RiskResult(score, level, EXPLANATION, METHOD_ID, VALIDATED)
