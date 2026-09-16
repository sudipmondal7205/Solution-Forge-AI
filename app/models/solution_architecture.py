from pydantic import BaseModel
from typing import List


class ArchitectureComponent(BaseModel):
    name: str
    responsibility: str


class DataStore(BaseModel):
    name: str
    purpose: str


class SolutionArchitecture(BaseModel):
    architecture_style: str

    components: List[ArchitectureComponent]

    data_stores: List[DataStore]

    data_flow: List[str]

    security: List[str]

    scalability: List[str]

    mvp_architecture: List[str]

    future_evolution: List[str]

    architecture_rationale: str

    risks: List[str]