from crewai import Crew, Process
from backend.agents.business_analyst import create_business_analyst
from backend.agents.solution_architect import create_solution_architect
from backend.agents.technology_advisor import create_technology_advisor
from backend.agents.delivery_planner import create_delivery_planner
from backend.core.llm import gemini_llm



def create_solution_crew(llm, user_input):
    business_analyst, business_analysis_task = create_business_analyst(llm, user_input)
    
    solution_architect, solution_architect_task = create_solution_architect(
        llm, user_input, context=[business_analysis_task]
    )
    
    technology_advisor, technology_advisor_task = create_technology_advisor(
        gemini_llm, user_input, context=[business_analysis_task, solution_architect_task]
    )
    
    delivery_planner, delivery_planner_task = create_delivery_planner(
        llm, user_input, context=[business_analysis_task, solution_architect_task, technology_advisor_task]
    )

    crew = Crew(
        agents=[
            business_analyst,
            solution_architect,
            technology_advisor,
            delivery_planner
        ],
        tasks=[
            business_analysis_task,
            solution_architect_task,
            technology_advisor_task,
            delivery_planner_task
        ],
        process=Process.sequential,
        verbose=True
    )

    return crew


def run_solution_consulting(llm, business_problem):

    crew = create_solution_crew(
        llm,
        business_problem
    )

    result = crew.kickoff()

    return result