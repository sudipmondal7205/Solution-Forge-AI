from crewai import Agent, Task
from config.llm import llm
from app.models.solution_architecture import SolutionArchitecture


solution_architect = Agent(
    role="Solution Architect",
    goal=(
        "Design a practical, scalable, secure, and constraint-aware "
        "system architecture based on the business requirements."
    ),
    backstory=(
        "You are an experienced solution architect who translates "
        "business and technical requirements into practical system "
        "architectures. You focus on MVP-first design, scalability, "
        "security, maintainability, and avoiding unnecessary complexity."
    ),
    llm=llm,
    verbose=True,
    allow_delegation=False
)

solution_architecture_task = Task(
    description=(
        "Analyze the user constraints and business requirements to design a complete system architecture.\n\n"
        "=== USER INPUT ===\n{user_input}\n\n"
        "=== BUSINESS ANALYSIS ===\n{business_analysis}\n\n"
        "Design the system architecture considering the MVP scope, expected traffic, "
        "timeline, and cloud preferences.\n\n"
        "You must define the architecture style, major components, database design, "
        "data flow, security, and scalability approach.\n\n"
        "Return ONLY valid JSON matching EXACTLY the expected schema."
    ),
    expected_output="A JSON object containing architecture_style, components, database, cache, data_flow, security, scalability, mvp_architecture, future_evolution, architecture_rationale, and architecture_risks.",
    agent=solution_architect,
    output_pydantic=SolutionArchitecture
)