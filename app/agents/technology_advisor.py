"""
Technology Advisor Agent
========================
Agent 4 in the Consulting Team System (CTS) pipeline.

This module implements the Technology Advisor (TA) agent using CrewAI.
It receives structured inputs from the Business Analyst (BA) and Solution Architect (SA)
agents and produces a comprehensive, justified technology stack recommendation natively
via a Crew execution.

Inputs  : UserInput + BusinessAnalysis + SolutionArchitecture
Output  : TechnologyRecommendation (structured JSON / Pydantic object)
"""

import os
import sys
import json
import logging
from typing import List, Optional

# Ensure standard output supports UTF-8 on Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

from dotenv import load_dotenv
from pydantic import BaseModel
from crewai import Agent, Crew, Process, Task
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
# SECTION 1: Pydantic Models (Input & Output Contracts)
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
# SECTION 2: CrewAI Custom Tools
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
# SECTION 3: CrewAI Agent & Task Definition
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
        "4. Include trade-offs, security controls, traffic scalability plans, and lock-in mitigation."
    ),
    expected_output="A structured TechnologyRecommendation object adhering to the specified schema.",
    agent=technology_advisor_agent,
    output_pydantic=TechnologyRecommendation,
)


# ==============================================================================
# SECTION 4: Execution Pipeline
# ==============================================================================

def run_technology_advisor(
    user_input: UserInput,
    business_analysis: BusinessAnalysis,
    solution_architecture: SolutionArchitecture,
) -> TechnologyRecommendation:
    """
    Execute the Technology Advisor task inside a standard CrewAI workflow.
    """
    logger.info("Executing Technology Advisor Agent via CrewAI...")

    crew = Crew(
        agents=[technology_advisor_agent],
        tasks=[technology_advisory_task],
        process=Process.sequential,
        verbose=True,
    )

    inputs = {
        "user_input": json.dumps(user_input.model_dump(), indent=2),
        "business_analysis": json.dumps(business_analysis.model_dump(), indent=2),
        "solution_architecture": json.dumps(solution_architecture.model_dump(), indent=2),
    }

    result = crew.kickoff(inputs=inputs)
    
    # Return the parsed Pydantic model produced directly by CrewAI
    return result.pydantic
