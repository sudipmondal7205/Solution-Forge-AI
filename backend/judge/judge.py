"""The Solution Judge.

Evaluates the generated solution against the original user requirements
and constraints.

The Judge combines:
1. LLM-based qualitative evaluation,
2. deterministic Python hard-constraint checks,
3. deterministic weighted scoring,
4. quality-band assignment.

The Judge does not generate or modify the solution blueprint itself.
"""
class JudgeAgent(BaseAgent[JudgeLLMOutput]):
    name = "JUDGE"
    label = "Solution Quality Judge"
    prompt_file = "judge"
    output_model = JudgeLLMOutput

    def build_user_prompt(self, context: dict[str, Any]) -> str:
        weights = context.get("rubric_weights") or {}

        weight_lines = "\n".join(
            f"- {name}: {value:g}%"
            for name, value in weights.items()
        )

        return (
            format_input_block(context["input"])

            + "\n\nRUBRIC WEIGHTS IN EFFECT\n"
            + weight_lines

            + """

JUDGING PRINCIPLES

1. Evaluate the generated solution against the original user
   requirements and constraints.

2. There is no single canonical architecture that must be reproduced.
   Multiple architectures and technology stacks can be valid.

3. A score of 100 represents complete satisfaction of the stated
   requirements and constraints, strong technical feasibility,
   appropriate scalability and security, realistic delivery planning,
   clear MVP focus, and absence of unnecessary complexity.

4. Do not penalize a solution merely because it differs from a
   different architecture you personally prefer.

5. Use evidence from the supplied BA, SA, TA, and DP outputs.

6. Distinguish explicit evidence from assumptions.

7. For scalability, do NOT give a high score merely because the
   requested traffic number is repeated. Evaluate whether the actual
   architecture, database, caching, load balancing, scaling strategy,
   and deployment approach are plausibly appropriate for the stated
   scale.

8. For technology alignment, check the user's technology preference,
   cloud preference, architecture requirements, delivery timeline,
   security needs, scalability needs, and the technology choices made
   by the Technology Advisor.

9. For timeline feasibility, compare the Delivery Planner's actual
   plan against the user's requested delivery timeline.

10. For MVP focus, distinguish MVP functionality from future evolution.

11. For over-engineering, penalize unnecessary services,
    infrastructure, technologies, or complexity that are not justified
    by the requirements.

12. Do not invent missing evidence.

13. Provide evidence for every criterion.

14. Do not calculate the overall score. The application calculates
    the weighted score and constraint penalties separately.

15. Return only the required evaluation JSON.
"""

            + "\n\nBUSINESS ANALYST OUTPUT\n"
            + format_upstream(
                "BUSINESS ANALYST OUTPUT",
                context["business_analyst"],
            )

            + "\n\nSOLUTION ARCHITECT OUTPUT\n"
            + format_upstream(
                "SOLUTION ARCHITECT OUTPUT",
                context["solution_architect"],
            )

            + "\n\nTECHNOLOGY ADVISOR OUTPUT\n"
            + format_upstream(
                "TECHNOLOGY ADVISOR OUTPUT",
                context["technology_advisor"],
            )

            + "\n\nDELIVERY PLANNER OUTPUT\n"
            + format_upstream(
                "DELIVERY PLANNER OUTPUT",
                context["delivery_planner"],
            )

            + """

Evaluate the complete solution against all nine rubric criteria.

For every criterion provide:
- score from 0 to 100
- assessment
- evidence
- issues
- improvements

Also provide:
- strengths
- weaknesses
- critical issues
- recommended improvements
- cross-agent consistency assessment
- concise judge summary

Produce the evaluation JSON.
"""
        )