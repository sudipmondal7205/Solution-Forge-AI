"""
models.py
=========
Plain-Python mirrors of the Pydantic models the backend team already agreed
on (see the team's shared "TA.txt" contract doc). These are NOT used for
validation here (validators.py owns frontend validation) — they exist so
that:

  1. The backend engineer can see, in one place, the exact field names and
     types the frontend expects in every API response.
  2. The frontend code (views/*.py) can use dot-style access with sensible
     defaults instead of scattering `.get("x", {}).get("y", [])` everywhere.

If the backend's real Pydantic models ever rename a field, update the
`.get(...)` keys in `from_dict` below AND the docstring in config.py so the
two stay in sync.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List


def _join_items(items: Any) -> str:
    """Helper: join a list of strings into one comma-separated string."""
    if isinstance(items, str):
        return items
    if isinstance(items, (list, tuple)):
        return ", ".join(str(item) for item in items if item)
    return ""


# ---------------------------------------------------------------------------
# UserInput — sent BY the frontend TO the backend (POST /consultations)
# ---------------------------------------------------------------------------
@dataclass
class UserInput:
    business_idea: str
    technology_preference: str
    cloud_preference: str
    expected_daily_traffic: int
    delivery_timeline_months: int
    data_hosting_country: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "business_idea": self.business_idea,
            "technology_preference": self.technology_preference,
            "cloud_preference": self.cloud_preference,
            "expected_daily_traffic": self.expected_daily_traffic,
            "delivery_timeline_months": self.delivery_timeline_months,
            "data_hosting_country": self.data_hosting_country,
        }


# ---------------------------------------------------------------------------
# Agent outputs — received FROM the backend (GET /consultations/{id}/result)
# ---------------------------------------------------------------------------
@dataclass
class BusinessAnalysis:
    problem_statement: str = ""
    users: List[str] = field(default_factory=list)
    stakeholders: List[str] = field(default_factory=list)
    functional_requirements: List[str] = field(default_factory=list)
    non_functional_requirements: List[str] = field(default_factory=list)
    mvp_scope: List[str] = field(default_factory=list)
    future_scope: List[str] = field(default_factory=list)
    constraints: List[str] = field(default_factory=list)
    assumptions: List[str] = field(default_factory=list)
    risks: List[str] = field(default_factory=list)
    open_questions: List[str] = field(default_factory=list)

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> "BusinessAnalysis":
        d = d or {}
        return BusinessAnalysis(
            problem_statement=d.get("problem_statement", ""),
            users=d.get("users", []),
            stakeholders=d.get("stakeholders", []),
            functional_requirements=d.get("functional_requirements", []),
            non_functional_requirements=d.get("non_functional_requirements", []),
            mvp_scope=d.get("mvp_scope", []),
            future_scope=d.get("future_scope", []),
            constraints=d.get("constraints", []),
            assumptions=d.get("assumptions", []),
            risks=d.get("risks", []),
            open_questions=d.get("open_questions", []),
        )


@dataclass
class SolutionArchitecture:
    architecture_style: str = ""
    components: List[Dict[str, str]] = field(default_factory=list)
    database: Dict[str, str] = field(default_factory=dict)
    cache: Dict[str, Any] = field(default_factory=dict)
    data_flow: List[str] = field(default_factory=list)
    security: List[str] = field(default_factory=list)
    scalability: List[str] = field(default_factory=list)
    mvp_architecture: List[str] = field(default_factory=list)
    future_evolution: List[str] = field(default_factory=list)
    architecture_rationale: str = ""
    architecture_risks: List[str] = field(default_factory=list)

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> "SolutionArchitecture":
        d = d or {}
        return SolutionArchitecture(
            architecture_style=d.get("architecture_style", ""),
            components=d.get("components", []),
            database=d.get("database", {}),
            cache=d.get("cache", {}),
            data_flow=d.get("data_flow", []),
            security=d.get("security", []),
            scalability=d.get("scalability", []),
            mvp_architecture=d.get("mvp_architecture", []),
            future_evolution=d.get("future_evolution", []),
            architecture_rationale=d.get("architecture_rationale", ""),
            architecture_risks=d.get("architecture_risks", []),
        )


@dataclass
class TechnologyRecommendation:
    technologies: List[Dict[str, str]] = field(default_factory=list)
    cloud: Dict[str, Any] = field(default_factory=dict)
    technology_strategy: str = ""
    alternatives: List[Dict[str, str]] = field(default_factory=list)
    trade_offs: List[Dict[str, Any]] = field(default_factory=list)
    security_considerations: List[str] = field(default_factory=list)
    scalability_considerations: List[str] = field(default_factory=list)
    technology_risks: List[str] = field(default_factory=list)
    lock_in_considerations: List[str] = field(default_factory=list)

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> "TechnologyRecommendation":
        d = d or {}
        return TechnologyRecommendation(
            technologies=d.get("technologies", []),
            cloud=d.get("cloud", {}),
            technology_strategy=d.get("technology_strategy", ""),
            alternatives=d.get("alternatives", []),
            trade_offs=d.get("trade_offs", []),
            security_considerations=d.get("security_considerations", []),
            scalability_considerations=d.get("scalability_considerations", []),
            technology_risks=d.get("technology_risks", []),
            lock_in_considerations=d.get("lock_in_considerations", []),
        )


@dataclass
class DeliveryPlan:
    workstreams: List[Dict[str, Any]] = field(default_factory=list)
    team_roles: List[Dict[str, Any]] = field(default_factory=list)
    timeline: List[Dict[str, Any]] = field(default_factory=list)
    milestones: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    risks: List[Dict[str, str]] = field(default_factory=list)
    testing_strategy: List[str] = field(default_factory=list)
    deployment_strategy: str = ""
    release_strategy: str = ""
    future_evolution: List[str] = field(default_factory=list)

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> "DeliveryPlan":
        d = d or {}
        return DeliveryPlan(
            workstreams=d.get("workstreams", []),
            team_roles=d.get("team_roles") or d.get("team", []),
            timeline=d.get("timeline", []),
            milestones=d.get("milestones", []),
            dependencies=d.get("dependencies", []),
            risks=d.get("risks", []),
            testing_strategy=d.get("testing_strategy", []),
            deployment_strategy=d.get("deployment_strategy") or _join_items(d.get("deployment_plan", [])),
            release_strategy=d.get("release_strategy", ""),
            future_evolution=d.get("future_evolution") or d.get("future_scope", []),
        )


@dataclass
class ConsultationResult:
    """The full, combined payload returned by GET /consultations/{id}/result"""
    business_analysis: BusinessAnalysis = field(default_factory=BusinessAnalysis)
    solution_architecture: SolutionArchitecture = field(default_factory=SolutionArchitecture)
    technology_recommendation: TechnologyRecommendation = field(default_factory=TechnologyRecommendation)
    delivery_plan: DeliveryPlan = field(default_factory=DeliveryPlan)
    user_input: Dict[str, Any] = field(default_factory=dict)

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> "ConsultationResult":
        d = d or {}
        agent_outputs = d.get("agent_outputs") or d
        return ConsultationResult(
            business_analysis=BusinessAnalysis.from_dict(agent_outputs.get("business_analysis", {})),
            solution_architecture=SolutionArchitecture.from_dict(agent_outputs.get("solution_architecture", {})),
            technology_recommendation=TechnologyRecommendation.from_dict(agent_outputs.get("technology_recommendation", {})),
            delivery_plan=DeliveryPlan.from_dict(agent_outputs.get("delivery_plan", {})),
            user_input=d.get("user_input", {}),
        )
