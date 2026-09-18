"""
views/live_results_view.py
===========================
"Live Results" page — matches the mockup: a Consultation Details card, a
row of 4 agent-status pills (Business Analyst -> Solution Architect ->
Technology Advisor -> Delivery Planner) that clearly shows which agent is
currently running, which are done, and which are still waiting, followed
by a one-line summary banner + download button once complete, then the
full blueprint broken into sections.

Polling strategy
-----------------
While overall_status == "processing", this page polls
GET /consultations/{id}/status every config.STATUS_POLL_INTERVAL_SECONDS
seconds using a short sleep + st.rerun() loop (the standard Streamlit
pattern for live-updating pages). A manual "Refresh now" button is also
provided so the user isn't purely dependent on auto-refresh.
"""

import time

import streamlit as st

import api_client
import config
import styles
from api_client import ApiError
from models import ConsultationResult


def render() -> None:
    styles.page_header("Live Results")

    consultation_id = st.session_state.get("viewing_consultation_id") or st.session_state.get("active_consultation_id")
    if not consultation_id:
        st.info("No consultation selected yet. Start a new one from **New Consultation**, "
                 "or open a past one from **Chat History**.")
        return

    _render_consultation_details_card()

    try:
        status_payload = api_client.get_consultation_status(
            token=st.session_state["auth_token"], consultation_id=consultation_id,
        )
    except ApiError as err:
        st.error(str(err))
        return

    agents_status = status_payload.get("agents", {})
    overall_status = status_payload.get("overall_status", "processing")

    _render_agent_pipeline(agents_status)

    if overall_status == "failed":
        st.error("The consultation failed while running. Please try again or contact support.")
        return

    if overall_status != "completed":
        st.caption("Multi-agent context is being passed sequentially for blueprint creation.")
        col_refresh, _ = st.columns([1, 3])
        with col_refresh:
            st.button("🔄 Refresh now", key="live_results_refresh")
        time.sleep(config.STATUS_POLL_INTERVAL_SECONDS)
        st.rerun()
        return

    # overall_status == "completed" -> fetch full result and render blueprint
    try:
        result_payload = api_client.get_consultation_result(
            token=st.session_state["auth_token"], consultation_id=consultation_id,
        )
    except ApiError as err:
        st.error(str(err))
        return

    result = ConsultationResult.from_dict(result_payload)
    _render_ready_banner(consultation_id, result_payload)
    _render_summary_section(result)
    st.markdown("---")
    _render_full_blueprint(result)


def _render_consultation_details_card() -> None:
    summary = st.session_state.get("consultation_summary") or {}
    if not summary:
        return
    st.markdown('<div class="sf-card">', unsafe_allow_html=True)
    st.markdown('<div class="sf-card-title">📋 Consultation Details</div>', unsafe_allow_html=True)
    idea = summary.get("business_idea", "")
    idea_preview = (idea[:80] + "…") if len(idea) > 80 else idea
    st.markdown(
        f"**Business Idea:** {idea_preview}  \n"
        f"**Scale:** ~{summary.get('expected_daily_traffic', 0):,} Daily Active Users  \n"
        f"**Constraints:** {summary.get('delivery_timeline_months', '?')}-month MVP, "
        f"{summary.get('cloud_preference', '')} · {summary.get('data_hosting_country', '')}"
    )
    st.markdown("</div>", unsafe_allow_html=True)


def _render_agent_pipeline(agents_status: dict) -> None:
    cols = st.columns(len(config.AGENT_PIPELINE))
    for idx, (col, agent) in enumerate(zip(cols, config.AGENT_PIPELINE), start=1):
        status = agents_status.get(agent["key"], "pending")
        css_class = styles.agent_status_class(status)
        sub_label = {
            "done": "Done ✔",
            "in_progress": "Working now…",
            "pending": "Waiting",
            "error": "Error",
        }.get(status, "Waiting")
        with col:
            st.markdown(
                f"""<div class="sf-agent-pill {css_class}">
                        {idx}. {agent['label']}
                        <span class="sf-agent-sub">{sub_label}</span>
                    </div>""",
                unsafe_allow_html=True,
            )
    st.write("")


def _render_ready_banner(consultation_id: str, result_payload: dict) -> None:
    col_msg, col_btn = st.columns([3, 1.4])
    with col_msg:
        st.success("Your comprehensive solution blueprint is ready for delivery planning.")
    with col_btn:
        try:
            html_report = api_client.export_blueprint_html(
                token=st.session_state["auth_token"], consultation_id=consultation_id,
            )
            st.download_button(
                "⬇️ Download HTML Blueprint Report",
                data=html_report,
                file_name="solution_blueprint.html",
                mime="text/html",
                use_container_width=True,
            )
        except ApiError as err:
            st.warning(f"Report download unavailable: {err}")


def _render_summary_section(result: ConsultationResult) -> None:
    """
    A short, scannable summary shown right below the ready banner — pulls the
    single most important fact out of each of the four agent outputs so the
    user gets the gist before scrolling into the full blueprint.
    """
    st.markdown("### Summary")
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("Architecture Style", result.solution_architecture.architecture_style or "—")
    with c2:
        tech_count = len(result.technology_recommendation.technologies)
        st.metric("Technologies Selected", tech_count)
    with c3:
        team_size = sum(role.get("count", 0) for role in result.delivery_plan.team_roles)
        st.metric("Recommended Team Size", team_size)
    with c4:
        total_weeks = sum(phase.get("duration_weeks", 0) for phase in result.delivery_plan.timeline)
        st.metric("Estimated Duration", f"{total_weeks} weeks")

    if result.business_analysis.problem_statement:
        st.markdown(f"**Problem Statement:** {result.business_analysis.problem_statement}")


def _render_full_blueprint(result: ConsultationResult) -> None:
    col1, col2, col3 = st.columns(3)

    with col1:
        _render_delivery_overview(result)
        _render_recommended_stack(result)
        _render_implementation_workstreams(result)

    with col2:
        _render_technology_detail(result)
        _render_team_roles(result)

    with col3:
        _render_timeline_milestones(result)
        _render_risks(result)
        _render_future_evolution(result)


def _render_delivery_overview(result: ConsultationResult) -> None:
    st.markdown("**Delivery Overview**")
    dp = result.delivery_plan
    if dp.deployment_strategy:
        st.caption(dp.deployment_strategy)
    if dp.timeline:
        rows = "".join(
            f"<tr><td>{p.get('phase','')}</td><td>{p.get('duration_weeks','')} wks</td></tr>"
            for p in dp.timeline
        )
        st.markdown(
            f"""<table style="width:100%; font-size:0.9rem;">
                    <tr><th align="left">Phase</th><th align="left">Duration</th></tr>
                    {rows}
                </table>""",
            unsafe_allow_html=True,
        )
    else:
        st.caption("No delivery phases returned yet.")


def _render_recommended_stack(result: ConsultationResult) -> None:
    st.markdown("**Recommended Technology Stack**")
    technologies = result.technology_recommendation.technologies
    if not technologies:
        st.caption("No technology recommendations yet.")
        return
    for tech in technologies:
        st.markdown(f"- **{tech.get('technology','')}** ({tech.get('category','')})")


def _render_implementation_workstreams(result: ConsultationResult) -> None:
    st.markdown("**Implementation Workstreams**")
    workstreams = result.delivery_plan.workstreams
    if not workstreams:
        st.caption("No workstreams returned yet.")
        return
    for ws in workstreams:
        tasks = ", ".join(ws.get("tasks", []))
        st.markdown(f"- **{ws.get('name','')}**: {tasks}")


def _render_technology_detail(result: ConsultationResult) -> None:
    st.markdown("**Technology Rationale**")
    for tech in result.technology_recommendation.technologies:
        with st.expander(f"{tech.get('technology','')} — {tech.get('category','')}"):
            st.write(tech.get("reason", "No rationale provided."))

    cloud = result.technology_recommendation.cloud
    if cloud:
        st.markdown(f"**Cloud:** {cloud.get('provider','')} — {', '.join(cloud.get('services', []))}")


def _render_team_roles(result: ConsultationResult) -> None:
    st.markdown("**Team Roles**")
    roles = result.delivery_plan.team_roles
    if not roles:
        st.caption("No team roles returned yet.")
        return
    for role in roles:
        st.markdown(f"- {role.get('count','?')} x {role.get('role','')}")


def _render_timeline_milestones(result: ConsultationResult) -> None:
    st.markdown("**Delivery Timeline & Milestones**")
    milestones = result.delivery_plan.milestones
    if not milestones:
        st.caption("No milestones returned yet.")
        return
    for m in milestones:
        st.markdown(f"- {m}")


def _render_risks(result: ConsultationResult) -> None:
    st.markdown("**Delivery Risks & Mitigations**")
    risks = result.delivery_plan.risks
    if not risks:
        st.caption("No risks returned yet.")
        return
    for r in risks:
        st.markdown(f"- **{r.get('risk','')}** ({r.get('impact','')}) — _{r.get('mitigation','')}_")


def _render_future_evolution(result: ConsultationResult) -> None:
    st.markdown("**Future Evolution**")
    items = result.delivery_plan.future_evolution
    if not items:
        st.caption("No future roadmap items returned yet.")
        return
    for item in items:
        st.markdown(f"- {item}")
