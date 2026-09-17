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
from models.technology_advisor import TechnologyRecommendation
from app.config.llm import llm
from crewai import Agent, Task
from crewai.tools import tool
import requests


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")




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
    llm=llm,
    verbose=True,
    allow_delegation=False,
    max_iter=6,
    max_rpm=30,
    output_pydantic=TechnologyRecommendation
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