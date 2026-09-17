from pydantic import BaseModel
from typing import List


class DeliveryPlan(BaseModel):
    delivery_overview: str
    mvp_scope: List[str]
    future_scope: List[str]
    workstreams: List[str]
    timeline: List[str]
    team: List[str]
    dependencies: List[str]
    risks: List[str]
    testing_strategy: List[str]
    deployment_plan: List[str]
    maintenance_plan: List[str]
    assumptions: List[str]
    open_questions: List[str]