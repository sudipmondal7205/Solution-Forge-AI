from crewai import Agent, Task
from app.models.solution_architecture import SolutionArchitecture


def create_solution_architect(llm, user_input, business_analysis):

    solution_architect_agent = Agent(
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
        description=f"""
            Analyze the user constraints and business requirements to
            design a complete system architecture.

            === USER INPUT ===
            {user_input}

            === BUSINESS ANALYSIS ===
            {business_analysis}

            Design the system architecture considering the MVP scope,
            expected traffic, timeline, and cloud preferences.

            You must define:

            1. Architecture style
            2. Major system components
            3. Database design
            4. Cache strategy
            5. Data flow
            6. Security approach
            7. Scalability approach
            8. MVP architecture
            9. Future evolution
            10. Architecture rationale
            11. Architecture risks

            Important rules:

            - Respect the business requirements.
            - Prioritize MVP-first architecture.
            - Do not introduce unnecessary complexity.
            - Consider scalability and maintainability.
            - Consider security requirements.
            - Respect the user's constraints and preferences.
            - Do not make technology choices that contradict the
              business requirements.
            - Return ONLY valid JSON matching EXACTLY the expected schema.
        """,

        expected_output=(
            "A JSON object containing architecture_style, components, "
            "database, cache, data_flow, security, scalability, "
            "mvp_architecture, future_evolution, architecture_rationale, "
            "and architecture_risks."
        ),

        agent=solution_architect_agent,
        output_pydantic=SolutionArchitecture
    )

    return solution_architect_agent, solution_architecture_task