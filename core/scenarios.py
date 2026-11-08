"""Scenario definitions and a single recommendation path over cached points."""

from collections.abc import Mapping
from dataclasses import dataclass, replace

from core.constraints import Constraints
from core.generator import Candidate, SearchTrace, select_recommendation
from core.model import predict
from core.sensitivity import reassess_trace

SCENARIO_NAMES = ("No Constraints", "3 Months", "No Certificate", "Custom")


@dataclass(frozen=True)
class Scenario:
    name: str
    constraints: Constraints | None

    @property
    def enforce_feasibility(self) -> bool:
        return self.constraints is not None


@dataclass(frozen=True)
class ScenarioResult:
    scenario: Scenario
    trace: SearchTrace
    recommendation: Candidate | None
    status: str

    @property
    def distance(self) -> float | None:
        return self.recommendation.distance if self.recommendation else None


def scenario_definitions(custom: Constraints | None = None) -> tuple[Scenario, ...]:
    """Presets never inherit edits to Custom; practical scenarios forbid decreases."""
    three_months = Constraints(income_cannot_decrease=True)
    return (
        Scenario("No Constraints", None),
        Scenario("3 Months", three_months),
        Scenario("No Certificate", replace(three_months, can_obtain_certification=False)),
        Scenario("Custom", replace(custom if custom is not None else Constraints(), income_cannot_decrease=True)),
    )


def evaluate_scenarios(
    baseline: SearchTrace,
    *,
    normalization: Mapping[str, float] | None = None,
    lambda_value: float = 10.0,
    custom: Constraints | None = None,
) -> dict[str, ScenarioResult]:
    """Reassess the same points in all scenarios, never regenerate applications.

    In No Constraints, practical flags are diagnostic and are not enforced.
    Domains and immutability remain mandatory in select_recommendation.
    """
    results = {}
    for scenario in scenario_definitions(custom):
        trace = reassess_trace(baseline, normalization=normalization, lambda_value=lambda_value,
                               constraints=scenario.constraints)
        best = select_recommendation(trace.candidates, enforce_feasibility=scenario.enforce_feasibility)
        status = "Already Accepted" if predict(baseline.original) else "Found" if best else "No feasible CF"
        results[scenario.name] = ScenarioResult(scenario, trace, best, status)
    return results
