import queue
import threading
import json
import sys
import os

# Ensure the backend module can be found
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from backend.core.llm import llm
from backend.services.orchestration import create_solution_crew
from backend.models.user_input import UserInput

# 1. Define a mock user input
mock_user_input = {
    "business_idea": "Healthcare Appointment & Patient Management Platform. Patients can register, search doctors, book appointments.",
    "technology_preference": "Open-source",
    "cloud_preference": "AWS",
    "expected_daily_traffic": 20000,
    "delivery_timeline_months": 6,
    "data_hosting_country": "India"
}

print("🚀 Starting Streaming SolutionForge AI Consulting...\n")

# 2. Setup the Queue and State
message_queue = queue.Queue()
agent_names = ["Business Analyst", "Solution Architect", "Technology Advisor", "Delivery Planner"]
state = {"index": 0}

# 3. The Callback (fires when ONE agent finishes)
def on_task_completed(task_output):
    idx = state["index"]
    if idx < len(agent_names):
        agent_name = agent_names[idx]
        
        # Try to extract the structured data
        if hasattr(task_output, 'pydantic') and task_output.pydantic:
            data = task_output.pydantic.model_dump(mode="json")
        elif hasattr(task_output, 'json_dict') and task_output.json_dict:
            data = task_output.json_dict
        else:
            data = {"raw": str(task_output)}
            
        # Push to queue immediately!
        message_queue.put({"agent": agent_name, "data": data})
        state["index"] += 1

# 4. The Background Thread Function
def run_crew():
    try:
        # Initialize
        crew_input = UserInput(**mock_user_input)
        crew = create_solution_crew(llm, crew_input)
        
        # Attach the callback to every task
        for task in crew.tasks:
            task.callback = on_task_completed
            
        # Block and run (in this background thread)
        crew.kickoff()
        
        # Send poison pill to signal completion
        message_queue.put(None) 
    except Exception as e:
        message_queue.put({"error": str(e)})
        message_queue.put(None)

# 5. Start the background thread
threading.Thread(target=run_crew).start()

# 6. Main Thread: Listen to the queue (Simulating what FastAPI's StreamingResponse does)
while True:
    # This blocks until an agent pushes data to the queue
    msg = message_queue.get() 
    
    if msg is None:
        print("\n✅ Consulting Complete! All agents finished.")
        break
        
    if "error" in msg:
        print(f"\n❌ Error occurred: {msg['error']}")
        break
        
    # Print the output the exact moment it arrives
    print(f"\n======================================================")
    print(f"🎉 STREAM EVENT RECEIVED: {msg['agent']} finished!")
    print(f"======================================================")
    
    # Pretty print just the first 500 characters of the JSON to prove it works
    json_str = json.dumps(msg['data'], indent=2)
    print(json_str[:500] + "\n... [truncated] ...\n")