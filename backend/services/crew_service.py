import json
import queue
import threading
import crewai.llms.cache as _crewai_cache
from backend.core.sanitize import sanitize_output
from backend.db.database import complete_consultation, update_agent_output
from backend.models.user_input import UserInput as CrewUserInput
from backend.services.orchestration import create_solution_crew
from backend.core.llm import llm


_crewai_cache.mark_cache_breakpoint = lambda message: message



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
                    return sanitize_output(val.model_dump(mode="json"))
                return sanitize_output(dict(val))
            except Exception:
                pass
    raw = getattr(task_output, "raw", None) or str(task_output)
    return sanitize_output({"raw": raw})



def start_consultation_stream(consultation_id: str, user_input: dict):
    """
    Starts the CrewAI process in a background thread and returns a generator
    that yields Server-Sent Events (SSE) as each agent finishes.
    """
    message_queue = queue.Queue()
    
    state = {"task_index": 0}
    def on_task_completed(task_output):
        """This callback fires every time one agent finishes its task."""
        idx = state["task_index"]
        if idx < len(AGENT_KEYS):
            agent_key = AGENT_KEYS[idx]
            data = _output_to_dict(task_output)
            
            update_agent_output(consultation_id, agent_key, data)
            
            message_queue.put({
                "event": "agent_finished",
                "agent": agent_key,
                "consultation_id": consultation_id,
                "data": data
            })
            state["task_index"] += 1

    def run_crew():
        """The blocking function that runs in the background thread."""
        try:
            crew_input = CrewUserInput(**user_input)
            crew = create_solution_crew(llm, crew_input)
            
            for task in crew.tasks:
                task.callback = on_task_completed

            crew.kickoff()
            
            complete_consultation(consultation_id, None, None)
            
            message_queue.put({
                "event": "complete",
                "consultation_id": consultation_id,
                "message": "All agents finished successfully."
            })
        except Exception as e:
            message_queue.put({
                "event": "error",
                "consultation_id": consultation_id,
                "message": str(e)
            })
        finally:
            message_queue.put(None) 
    threading.Thread(target=run_crew).start()
    def event_generator():
        while True:
            msg = message_queue.get()
            if msg is None:
                break
            
            yield f"data: {json.dumps(msg)}\n\n"
    return event_generator