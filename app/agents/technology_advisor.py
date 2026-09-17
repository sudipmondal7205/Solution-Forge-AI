"""
Technology Advisor Agent
========================
 

Receives the common UserInput plus the Business Analyst (BA) and Solution
Architect (SA) outputs, and produces a specific, justified technology stack
recommendation.

Inputs  : UserInput + BusinessAnalysis + SolutionArchitecture
          (JSON strings, dicts, or Pydantic instances)
Output  : TechnologyRecommendation (structured Pydantic object)
"""

import os
import sys
import json
import logging
from typing import List, Union

# Ensure UTF-8 stdout/stderr on Windows consoles
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


# ==============================================================================
# SECTION 1: LLM Setup (Gemini)
# ==============================================================================

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not GEMINI_API_KEY:
    raise EnvironmentError("GEMINI_API_KEY is not set in environment variables.")


gemini_llm = LLM(
    model="gemini/gemini-3.5-flash-lite",
    api_key=GEMINI_API_KEY,
    temperature=0.2,
    max_output_tokens=8192,
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


# --- TA Output Models (matches the contract you pasted) ---

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
    This is the output contract passed to the Task Advisor and Delivery Planner.
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
# SECTION 3: CrewAI Custom Tool (Serper.dev)
# ==============================================================================

@tool("Search Internet via Serper")
def serper_search_tool(query: str) -> str:
    """
    Perform a Google search via Serper.dev to find current technology comparisons,
    library versions, cloud service capabilities, or framework benchmarks.
    """
    serper_api_key = os.getenv("SERPER_API_KEY")
    if not serper_api_key:
        return "Search unavailable: SERPER_API_KEY not set."

    try:
        response = requests.post(
            "https://google.serper.dev/search",
            headers={
                "X-API-KEY": serper_api_key,
                "Content-Type": "application/json",
            },
            json={"q": query, "num": 5},
            timeout=15,
        )
        response.raise_for_status()
        results = response.json()

        lines = []
        for r in results.get("organic", [])[:5]:
            lines.append(
                f"- {r.get('title', '')}\n"
                f"  URL: {r.get('link', '')}\n"
                f"  {r.get('snippet', '')}"
            )

        kg = results.get("knowledgeGraph")
        if kg:
            lines.append(
                f"\nKnowledge Graph:\n  {kg.get('title', '')}: {kg.get('description', '')}"
            )

        return "\n".join(lines) if lines else "No results found."
    except Exception as exc:
        return f"Search error: {exc}"


# ==============================================================================
# SECTION 4: CrewAI Agent & Task Definition
# ==============================================================================

technology_advisor_agent = Agent(
    role="Principal Technology Advisor",
    goal=(
        "Select a specific, well-justified technology stack that strictly aligns "
        "with the solution architecture, client constraints, cloud preferences, "
        "and delivery timeline."
    ),
    backstory=(
        "You are a senior technical advisor with deep expertise in full-stack "
        "architecture, cloud infrastructure, database selection, and DevOps "
        "practices. You rigorously evaluate open-source vs enterprise frameworks, "
        "scalability limits, security frameworks, and vendor lock-in. You use web "
        "search to validate current best practices before recommending a stack."
    ),
    tools=[serper_search_tool],
    llm=gemini_llm,
    verbose=True,
    allow_delegation=False,
    max_iter=6,
    max_rpm=30,
)


technology_advisory_task = Task(
    description=(
        "Analyze the inputs below and recommend a complete, production-ready "
        "technology stack.\n\n"
        "=== USER INPUT ===\n{user_input}\n\n"
        "=== BUSINESS ANALYSIS ===\n{business_analysis}\n\n"
        "=== SOLUTION ARCHITECTURE ===\n{solution_architecture}\n\n"
        "Requirements:\n"
        "1. Select specific tools for at least these categories: Backend, "
        "   Database, Cache, Frontend, Containerization.\n"
        "2. Respect technology_preference (e.g. open-source) and "
        "   cloud_preference (e.g. AWS).\n"
        "3. Include alternatives, trade_offs, security_considerations, "
        "   scalability_considerations, technology_risks, lock_in_considerations.\n"
        "4. Honour delivery_timeline_months, expected_daily_traffic, "
        "   data_hosting_country.\n\n"
        "You MUST call the 'Search Internet via Serper' tool atleast once before giving the response.\n\n"
        "Return ONLY valid JSON matching EXACTLY this schema — no extra fields, "
        "no missing fields, no markdown fences:\n\n"
        "{\n"
        '  "technologies": [\n'
        '    {"category": "Backend", "technology": "FastAPI", "reason": "..."}\n'
        "  ],\n"
        '  "cloud": {"provider": "AWS", "services": ["EC2", "RDS"]},\n'
        '  "technology_strategy": "Open-source-first",\n'
        '  "alternatives": [\n'
        '    {"category": "Backend", "recommended": "FastAPI", '
        '"alternative": "Spring Boot", "reason": "..."}\n'
        "  ],\n"
        '  "trade_offs": [\n'
        '    {"decision": "PostgreSQL", '
        '"advantages": ["..."], "disadvantages": ["..."]}\n'
        "  ],\n"
        '  "security_considerations": ["..."],\n'
        '  "scalability_considerations": ["..."],\n'
        '  "technology_risks": ["..."],\n'
        '  "lock_in_considerations": ["..."]\n'
        "}\n"
    ),
    expected_output=(
        "A single JSON object with keys: technologies, cloud, "
        "technology_strategy (string), alternatives, trade_offs, "
        "security_considerations, scalability_considerations, "
        "technology_risks, lock_in_considerations."
    ),
    agent=technology_advisor_agent,
)
# ==============================================================================
# SECTION 5: Execution Pipeline
# ==============================================================================

def _normalize_to_json_str(
    val: Union[str, dict, BaseModel],
    model_cls: type,
) -> str:
    """Convert incoming string / dict / Pydantic instance into indented JSON."""
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


def _strip_code_fences(raw: str) -> str:
    """Remove ```json ... ``` or ``` ... ``` wrappers if present."""
    s = raw.strip()
    if s.startswith("```json"):
        s = s[len("```json"):]
    elif s.startswith("```"):
        s = s[len("```"):]
    if s.endswith("```"):
        s = s[:-len("```")]
    return s.strip()


def run_technology_advisor(
    user_input: Union[str, dict, UserInput],
    business_analysis: Union[str, dict, BusinessAnalysis],
    solution_architecture: Union[str, dict, SolutionArchitecture],
) -> TechnologyRecommendation:
    """
    Execute the Technology Advisor inside a CrewAI workflow.

    Accepts raw JSON strings, Python dicts, or Pydantic instances.
    Returns a validated TechnologyRecommendation.
    """
    logger.info("Executing Technology Advisor Agent via CrewAI...")

    inputs = {
        "user_input": _normalize_to_json_str(user_input, UserInput),
        "business_analysis": _normalize_to_json_str(business_analysis, BusinessAnalysis),
        "solution_architecture": _normalize_to_json_str(
            solution_architecture, SolutionArchitecture
        ),
    }

    crew = Crew(
        agents=[technology_advisor_agent],
        tasks=[technology_advisory_task],
        process=Process.sequential,
        verbose=True,
    )

    result = crew.kickoff(inputs=inputs)

    # 1) Prefer structured pydantic output if CrewAI produced it.
    if hasattr(result, "pydantic") and result.pydantic:
        return result.pydantic
    if (
        hasattr(result, "tasks_output")
        and result.tasks_output
        and getattr(result.tasks_output[0], "pydantic", None)
    ):
        return result.tasks_output[0].pydantic

    # 2) Fall back to manual JSON parsing.
    raw_str = _strip_code_fences(getattr(result, "raw", str(result)))
    return TechnologyRecommendation.model_validate_json(raw_str)
