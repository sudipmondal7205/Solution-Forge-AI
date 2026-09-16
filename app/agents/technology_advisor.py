"""
Technology Advisor Agent
========================
Agent 4 

This module implements the Technology Advisor (TA) agent using CrewAI.
It receives structured inputs from the Business Analyst (BA) and Solution Architect (SA)
agents and produces a comprehensive, justified technology stack recommendation natively
via a Crew execution.

Inputs  : UserInput + BusinessAnalysis + SolutionArchitecture (JSON strings, Dicts, or Pydantic instances)
Output  : TechnologyRecommendation (structured Pydantic object)
"""

import os
import sys
import json
import logging
from typing import List, Optional, Union

# Ensure standard output supports UTF-8 on Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

from dotenv import load_dotenv
from pydantic import BaseModel
from crewai import Agent, Crew, Process, Task, LLM
from crewai.tools import tool
import requests

# ---------------------------------------------------------------------------
# Environment & Logging
# ---------------------------------------------------------------------------
load_dotenv(override=True)

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("TechnologyAdvisor")

# Environment setup for OpenRouter fallback routing
openrouter_key = os.getenv("OPENROUTER_API_KEY")
if openrouter_key:
    os.environ["OPENAI_API_KEY"] = openrouter_key
    os.environ["OPENAI_API_BASE"] = "https://openrouter.ai/api/v1"


# ==============================================================================
# SECTION 1: LLM Setup
# ==============================================================================

# LLM configuration set to inclusionai/ling-3.0-flash-vl:free via OpenRouter
openrouter_llm = LLM(
    model="openrouter/inclusionai/ling-3.0-flash-vl:free",
    api_key=openrouter_key,
    base_url="https://openrouter.ai/api/v1",
    temperature=0.2,
)


# ==============================================================================
# SECTION 2: Pydantic Models (Input & Output Contracts)
# ==============================================================================

class UserInput(BaseModel):
    """Raw project requirements captured from the client."""
    business_idea: str
    technology_preference: str
    cloud_preference: str
    expected_daily_traffic: int
    delivery_timeline_months: int
    data_hosting_country: str


class BusinessAnalysis(BaseModel):
    """Structured output produced by the Business Analyst (BA) agent."""
    problem_statement: str
    users: List[str]
    stakeholders: List[str]
    functional_requirements: List[str]
    non_functional_requirements: List[str]
    mvp_scope: List[str]
    future_scope: List[str]
    constraints: List[str]
    assumptions: List[str]
    risks: List[str]
    open_questions: List[str]


class Component(BaseModel):
    """A single architectural component."""
    name: str
    responsibility: str


class DatabaseDesign(BaseModel):
    """Database layer specification."""
    type: str
    purpose: str


class CacheDesign(BaseModel):
    """Cache layer specification."""
    required: bool
    purpose: str


class SolutionArchitecture(BaseModel):
    """Structured output produced by the Solution Architect (SA) agent."""
    architecture_style: str
    components: List[Component]
    database: DatabaseDesign
    cache: CacheDesign
    data_flow: List[str]
    security: List[str]
    scalability: List[str]
    mvp_architecture: List[str]
    future_evolution: List[str]
    architecture_rationale: str
    architecture_risks: List[str]


# --- TA Output Models ---

class Technology(BaseModel):
    """A single technology recommendation for a specific category."""
    category: str
    technology: str
    reason: str


class CloudServices(BaseModel):
    """Cloud provider and specific services recommended."""
    provider: str
    services: List[str]


class Alternative(BaseModel):
    """An alternative technology option with justification for the primary choice."""
    category: str
    recommended: str
    alternative: str
    reason: str


class TradeOff(BaseModel):
    """Advantages and disadvantages for a key decision."""
    decision: str
    advantages: List[str]
    disadvantages: List[str]


class TechnologyRecommendation(BaseModel):
    """
    Complete technology recommendation produced by the Technology Advisor agent.
    This is the output contract passed to the Delivery Planner (DP) agent.
    """
    technologies: List[Technology]
    cloud: CloudServices
    technology_strategy: str
    alternatives: List[Alternative]
    trade_offs: List[TradeOff]
    security_considerations: List[str]
    scalability_considerations: List[str]
    technology_risks: List[str]
    lock_in_considerations: List[str]


# ==============================================================================
# SECTION 3: CrewAI Custom Tools
# ==============================================================================

@tool("Search Internet via Serper")
def serper_search_tool(query: str) -> str:
    """
    Perform a Google search via Serper.dev to find up-to-date tech stack benchmarks,
    cloud service capabilities, or library recommendations.
    """
    serper_api_key = os.getenv("SERPER_API_KEY")
    if not serper_api_key:
        return "Search unavailable: SERPER_API_KEY not set."

    try:
        response = requests.post(
            "https://google.serper.dev/search",
            headers={"X-API-KEY": serper_api_key, "Content-Type": "application/json"},
            json={"q": query},
            timeout=10,
        )
        response.raise_for_status()
        results = response.json()

        if "organic" in results:
            snippets = [
                f"- {r.get('title')}: {r.get('snippet')}"
                for r in results["organic"][:3]
            ]
            return "\n".join(snippets)

        return "No organic results found."
    except Exception as exc:
        return f"Search error: {exc}"


# ==============================================================================
# SECTION 4: CrewAI Agent & Task Definition
# ==============================================================================

technology_advisor_agent = Agent(
    role="Principal Technology Advisor",
    goal=(
        "Select a specific, well-justified technology stack that strictly aligns with "
        "the architecture design, client constraints, cloud preferences, and delivery timeline."
    ),
    backstory=(
        "You are a senior technical advisor with deep expertise in full-stack architecture, "
        "cloud infrastructure, database selection, and DevOps practices. You rigorously evaluate "
        "open-source vs. enterprise frameworks, scalability limits, security frameworks, and vendor lock-in."
    ),
    tools=[serper_search_tool],
    llm=openrouter_llm,
    verbose=True,
    allow_delegation=False,
)

technology_advisory_task = Task(
    description=(
        "Analyze the provided inputs from the client, Business Analyst, and Solution Architect. "
        "Recommend a complete, production-ready technology stack.\n\n"
        "Input Context:\n"
        "=== USER INPUT ===\n{user_input}\n\n"
        "=== BUSINESS ANALYSIS ===\n{business_analysis}\n\n"
        "=== SOLUTION ARCHITECTURE ===\n{solution_architecture}\n\n"
        "Requirements:\n"
        "1. Select specific tools for Backend, Database, Cache, Frontend, and Containerization.\n"
        "2. Respect client preferences regarding cloud provider and open-source strategy.\n"
        "3. Provide at least one valid alternative technology choice per major component.\n"
        "4. Include trade-offs, security controls, traffic scalability plans, and lock-in mitigation.\n"
        "5. Output MUST be valid JSON adhering strictly to the TechnologyRecommendation schema."
    ),
    expected_output="A JSON object matching the TechnologyRecommendation schema.",
    agent=technology_advisor_agent,
    # Note: Handled via safe JSON parsing in run_technology_advisor to prevent free-tier provider schema error
)


# ==============================================================================
# SECTION 5: Execution Pipeline
# ==============================================================================

def run_technology_advisor(
    user_input: Union[str, dict, UserInput],
    business_analysis: Union[str, dict, BusinessAnalysis],
    solution_architecture: Union[str, dict, SolutionArchitecture],
) -> TechnologyRecommendation:
    """
    Execute the Technology Advisor task inside a standard CrewAI workflow.
    
    Accepts raw JSON strings, Python dicts, or Pydantic instances.
    """
    logger.info("Executing Technology Advisor Agent via CrewAI...")

    def _normalize_to_json_str(val: Union[str, dict, BaseModel], model_cls: type) -> str:
        """Converts incoming string/dict/Pydantic into formatted JSON string."""
        if isinstance(val, str):
            parsed = model_cls.model_validate_json(val)
            return parsed.model_dump_json(indent=2)
        elif isinstance(val, dict):
            parsed = model_cls.model_validate(val)
            return parsed.model_dump_json(indent=2)
        elif isinstance(val, BaseModel):
            return val.model_dump_json(indent=2)
        else:
            raise TypeError(f"Unsupported input type for {model_cls.__name__}: {type(val)}")

    inputs = {
        "user_input": _normalize_to_json_str(user_input, UserInput),
        "business_analysis": _normalize_to_json_str(business_analysis, BusinessAnalysis),
        "solution_architecture": _normalize_to_json_str(solution_architecture, SolutionArchitecture),
    }

    crew = Crew(
        agents=[technology_advisor_agent],
        tasks=[technology_advisory_task],
        process=Process.sequential,
        verbose=True,
    )

    result = crew.kickoff(inputs=inputs)
    
    # Check for direct Pydantic attribute first
    if hasattr(result, "pydantic") and result.pydantic:
        return result.pydantic
    elif hasattr(result, "tasks_output") and result.tasks_output and result.tasks_output[0].pydantic:
        return result.tasks_output[0].pydantic

    # Clean codeblock wrappers if present and parse manually
    raw_str = result.raw.strip()
    if raw_str.startswith("```json"):
        raw_str = raw_str[7:]
    if raw_str.startswith("```"):
        raw_str = raw_str[3:]
    if raw_str.endswith("```"):
        raw_str = raw_str[:-3]

    return TechnologyRecommendation.model_validate_json(raw_str.strip())
