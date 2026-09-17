from crewai import Agent, Task


def create_business_analyst_agent(llm):
    business_analyst = Agent(
        role="Business Analyst",

        goal=(
            "Understand the business problem and convert it into clear, "
            "structured, and actionable business requirements."
        ),

        backstory=(
            "You are an experienced Business Analyst who identifies users "
            "and stakeholders, extracts functional and non-functional "
            "requirements, defines MVP and future scope, and identifies "
            "assumptions, constraints, risks, and open questions. "
            "You focus on business requirements and avoid unnecessary "
            "technical or architectural decisions."
        ),

        llm=llm,
        verbose=True,
        allow_delegation=False
    )

    return business_analyst


def create_business_analyst_task(business_analyst, business_problem):

    business_analysis_task = Task(
        description=f"""
Analyze the following business problem:

{business_problem}

Identify:
1. Problem statement
2. Users
3. Stakeholders
4. Functional requirements
5. Non-functional requirements
6. MVP scope
7. Future scope
8. Constraints
9. Assumptions
10. Risks
11. Open questions

Rules:
- Focus on business requirements.
- Do not select technologies or design architecture.
- Do not invent unnecessary requirements.
- Separate MVP and future scope.
- Put missing information in open_questions.
- Return valid JSON only.
""",

        expected_output="""
{
  "problem_statement": "...",

  "users": [
    "..."
  ],

  "stakeholders": [
    "..."
  ],

  "functional_requirements": [
    "..."
  ],

  "non_functional_requirements": [
    "..."
  ],

  "mvp_scope": [
    "..."
  ],

  "future_scope": [
    "..."
  ],

  "constraints": [
    "..."
  ],

  "assumptions": [
    "..."
  ],

  "risks": [
    "..."
  ],

  "open_questions": [
    "..."
  ]
}
""",

        agent=business_analyst
    )

    return business_analysis_task
