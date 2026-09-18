"""
Crew service — the bridge between FastAPI and the CrewAI agentic workflow.

Flow:
  consultation created  ->  crew runs (BA -> SA -> TA -> DP)  ->  each agent's
  output is saved into the consultation document in MongoDB.

This module imports the existing CrewAI pipeline from the repo's `app/` folder
(untouched). It is the single place the backend talks to the agents.
"""

import os
import sys
from typing import Callable, Optional

# Make the repo root importable so we can `import app.*` (CrewAI pipeline).
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

# Workaround for crewai issue #5886: CrewAI injects a `cache_breakpoint` flag
# into every message for NON-Anthropic providers (e.g. Cohere), which Cohere's
# API rejects. This no-op patch prevents the injection before it reaches Cohere.
import crewai.llms.cache as _crewai_cache  # noqa: E402
_crewai_cache.mark_cache_breakpoint = lambda message: message

from ..db.database import update_agent_output  # noqa: E402

# Order of agents in the CrewAI pipeline.
AGENT_KEYS = [
    "business_analysis",
    "solution_architecture",
    "technology_recommendation",
    "delivery_plan",
]


def _output_to_dict(task_output) -> dict:
    """Convert a CrewAI TaskOutput into a plain JSON-friendly dict."""
    for attr in ("pydantic", "json_dict"):
        val = getattr(task_output, attr, None)
        if val is not None:
            try:
                if hasattr(val, "model_dump"):
                    return val.model_dump(mode="json")
                return dict(val)
            except Exception:
                pass
    raw = getattr(task_output, "raw", None) or str(task_output)
    return {"raw": raw}


def _get_llm():
    """Load the shared LLM (Cohere) once, lazily."""
    from dotenv import load_dotenv
    load_dotenv(override=True)
    from app.config.llm import llm

    # Cohere's API rejects CrewAI's "native tool calling" payloads (it sends a
    # `strict` field Cohere does not accept). Fall back to classic ReAct-style
    # tool calling, which works with Cohere.
    llm.supports_function_calling = lambda: False

    return llm


def run_consultation(
    consultation_id: str,
    user_input: dict,
    progress: Optional[Callable[[str, dict], None]] = None,
) -> dict:
    """
    Run the full CrewAI pipeline for one consultation and save every agent
    output into MongoDB.

    - consultation_id : Mongo document _id of the consultation
    - user_input      : validated dict of the 6 user-input fields
    - progress        : optional callback(key, output_dict) called after each
                        agent finishes (used to stream progress to the UI)
    """
    from app.models.user_input import UserInput as CrewUserInput
    from app.orchestration import create_solution_crew

    llm = _get_llm()
    crew_input = CrewUserInput(**user_input)

    crew = create_solution_crew(llm, crew_input)
    result = crew.kickoff()

    tasks_output = list(result.tasks_output or [])
    saved: dict[str, dict] = {}

    for i, agent_key in enumerate(AGENT_KEYS):
        if i >= len(tasks_output):
            break
        data = _output_to_dict(tasks_output[i])
        update_agent_output(consultation_id, agent_key, data)
        saved[agent_key] = data
        if progress:
            progress(agent_key, data)

    return {"agent_outputs": saved, "final_result": str(result)}