"""
views/consultation_view.py
===========================
"New Consultation" page — matches the mockup: business idea textarea,
technology preference, cloud preference, expected daily traffic, delivery
timeline slider, country search-select, and a "Generate Solution Blueprint"
submit button.

On submit, the page opens an SSE stream to POST /consultations and renders
agent outputs live as each agent finishes — no page navigation needed.
"""

import html

import streamlit as st
import api_client
import config
import session_state as ss
import styles
from api_client import ApiError
from models import UserInput
from validators import consultation_errors, validate_consultation_form


# Map backend agent keys to human-readable labels
AGENT_LABELS = {
    "business_analysis": "Business Analyst",
    "solution_architecture": "Solution Architect",
    "technology_recommendation": "Technology Advisor",
    "delivery_plan": "Delivery Planner",
}

AGENT_ORDER = [
    "business_analysis",
    "solution_architecture",
    "technology_recommendation",
    "delivery_plan",
]


def render() -> None:
    if "consult_submitted" not in st.session_state:
        st.session_state.consult_submitted = False

    if st.session_state.consult_submitted:
        # Already submitted — show header + results directly.
        # IMPORTANT: if the stream already finished, re-render the SAVED
        # results instead of POSTing a brand-new consultation on every
        # Streamlit rerun (this was creating duplicate consultations).
        col_title, col_btn = st.columns([5, 1])
        with col_title:
            styles.page_header("Live Blueprint")
        with col_btn:
            if st.button("← Back", key="new_consult_btn", use_container_width=True):
                st.session_state.consult_submitted = False
                st.session_state.pop("consult_results", None)
                st.session_state.pop("active_consultation_id", None)
                st.rerun()
        if st.session_state.get("consult_results"):
            _render_saved_results()
        else:
            _submit(**st.session_state.consult_form_data)
        return

    # --- First visit or after clicking Back: show the form ---
    styles.page_header("New Consultation")

    form_container = st.empty()
    with form_container.container():
        notice = st.session_state.pop("form_notice", None)
        if notice:
            st.error(notice)

        col_left, col_right = st.columns(2)

        with col_left:
            st.markdown('<div class="sf-section-label">Business Context</div>', unsafe_allow_html=True)
            business_idea = st.text_area(
                "Business Idea / Problem Statement",
                key="consult_business_idea",
                placeholder="Healthcare Patient Platform",
                height=160,
            )
            technology_preference = st.selectbox(
                "Technology Preference",
                options=config.TECHNOLOGY_PREFERENCE_OPTIONS,
                key="consult_tech_preference",
            )
            delivery_timeline_months = st.slider(
                "Delivery Timeline (Months)",
                min_value=0, max_value=10, value=0, step=1,
                key="consult_timeline",
                help="Starting at 0 — slide up to the number of months for delivery.",
            )

        with col_right:
            st.markdown('<div class="sf-section-label">Delivery Constraints</div>', unsafe_allow_html=True)
            cloud_preference = st.selectbox(
                "Cloud Preference",
                options=config.CLOUD_PREFERENCE_OPTIONS,
                key="consult_cloud_preference",
            )
            expected_daily_traffic = st.number_input(
                "Expected Daily Traffic",
                min_value=0, step=100, value=0, key="consult_daily_traffic",
                help="Approximate number of daily active users / requests. Starts at 0 — add it to unlock the button.",
            )
            data_hosting_country = st.selectbox(
                "Country",
                options=[""] + config.COUNTRY_OPTIONS,
                key="consult_country",
                format_func=lambda c: "Search a country..." if c == "" else c,
            )
        st.write("")
        is_valid = bool(
            business_idea.strip()
            and data_hosting_country
            and expected_daily_traffic > 0
            and delivery_timeline_months > 0
        )
        submit = st.button("🚀  Generate Solution Blueprint", key="consult_submit",
                     type="primary", use_container_width=True,
                     disabled=not is_valid)

    if submit:
        form_container.empty()
        st.session_state.consult_submitted = True
        st.session_state.consult_form_data = {
            "business_idea": business_idea,
            "technology_preference": technology_preference,
            "cloud_preference": cloud_preference,
            "expected_daily_traffic": expected_daily_traffic,
            "delivery_timeline_months": delivery_timeline_months,
            "data_hosting_country": data_hosting_country,
        }
        _submit(**st.session_state.consult_form_data)


def _submit(business_idea, technology_preference, cloud_preference,
            expected_daily_traffic, delivery_timeline_months, data_hosting_country) -> None:
    is_valid, error = validate_consultation_form(
        business_idea=business_idea,
        expected_daily_traffic=expected_daily_traffic,
        delivery_timeline_months=delivery_timeline_months,
        data_hosting_country=data_hosting_country,
    )
    if not is_valid:
        st.error(error)
        return

    user_input = UserInput(
        business_idea=business_idea.strip(),
        technology_preference=technology_preference,
        cloud_preference=cloud_preference,
        expected_daily_traffic=int(expected_daily_traffic),
        delivery_timeline_months=int(delivery_timeline_months),
        data_hosting_country=data_hosting_country,
    )

    # --- Agent pipeline status pills (updated live) ---
    pipeline_placeholder = st.empty()
    # --- Status message ---
    status_placeholder = st.empty()
    # --- Agent output appears below in horizontal tabs ---
    tabs = st.tabs([
        "Business Analyst", 
        "Solution Architect", 
        "Technology Advisor", 
        "Delivery Planner"
    ])
    
    # Create an empty placeholder inside each tab so we can update them live
    tab_placeholders = {
        "business_analysis": tabs[0].empty(),
        "solution_architecture": tabs[1].empty(),
        "technology_recommendation": tabs[2].empty(),
        "delivery_plan": tabs[3].empty(),
    }

    # Track which agents are done, in_progress, or pending
    agent_statuses = {key: "pending" for key in AGENT_ORDER}
    agent_results = {}

    def _render_pipeline():
        """Redraw the 4 agent status pills into the placeholder."""
        cols = pipeline_placeholder.columns(len(AGENT_ORDER))
        for idx, (col, key) in enumerate(zip(cols, AGENT_ORDER), start=1):
            status = agent_statuses[key]
            label = AGENT_LABELS[key]
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
                            {idx}. {label}
                            <span class="sf-agent-sub">{sub_label}</span>
                        </div>""",
                    unsafe_allow_html=True,
                )

    # Initial render — first agent starts immediately
    agent_statuses[AGENT_ORDER[0]] = "in_progress"
    _render_pipeline()
    status_placeholder.info("🚀 Starting your AI consulting team… **Business Analyst** is working…")

    try:
        stream = api_client.stream_consultation(
            token=st.session_state["auth_token"],
            user_input=user_input.to_dict(),
        )

        for event in stream:
            event_type = event.get("event")

            if event_type == "agent_finished":
                agent_key = event.get("agent", "")
                agent_data = event.get("data", {})

                # Mark this agent done
                agent_statuses[agent_key] = "done"
                agent_results[agent_key] = agent_data

                # Mark the NEXT agent as in_progress (if any)
                try:
                    current_idx = AGENT_ORDER.index(agent_key)
                    if current_idx + 1 < len(AGENT_ORDER):
                        next_key = AGENT_ORDER[current_idx + 1]
                        agent_statuses[next_key] = "in_progress"
                except ValueError:
                    pass

                # Re-render the pipeline pills
                _render_pipeline()

                status_placeholder.info(
                    f"✅ **{AGENT_LABELS.get(agent_key, agent_key)}** finished. "
                    f"({sum(1 for s in agent_statuses.values() if s == 'done')}/{len(AGENT_ORDER)} agents done)"
                )

                # Render this agent in its respective tab
                with tab_placeholders[agent_key].container():
                    _render_agent_output(agent_key, agent_results[agent_key])

            elif event_type == "complete":
                # All done
                _render_pipeline()
                status_placeholder.success(
                    "🎉 **All agents finished!** Your solution blueprint is ready. Click the tabs above to view details."
                )

                # Store the consultation id so the blueprint can be downloaded
                consultation_id = event.get("consultation_id") or st.session_state.get("active_consultation_id")
                if consultation_id:
                    st.session_state["active_consultation_id"] = consultation_id

                # Persist the finished results so later Streamlit reruns re-render
                # these instead of POSTing a duplicate consultation.
                st.session_state["consult_results"] = {
                    "agent_results": agent_results,
                    "agent_statuses": dict(agent_statuses),
                    "status_label": "completed",
                }

                st.markdown("")
                if consultation_id:
                    try:
                        html_report = api_client.export_blueprint_html(
                            token=st.session_state["auth_token"],
                            consultation_id=consultation_id,
                        )
                        st.download_button(
                            "📥 Download Blueprint (HTML)",
                            data=html_report,
                            file_name="blueprint.html",
                            mime="text/html",
                            type="primary",
                        )
                    except ApiError as dlerr:
                        st.warning(f"Blueprint ready, but download failed: {dlerr}")

            elif event_type == "error":
                status_placeholder.error(
                    f"❌ Pipeline error: {event.get('message', 'Unknown error')}"
                )
                return

    except ApiError as err:
        if getattr(err, "status_code", 0) == 422:
            # Backend rejected the input (e.g. prompt injection). Go back to
            # the New Consultation form and show WHY it was stopped.
            _reset_to_form(f"⛔ {err}")
        else:
            status_placeholder.error(str(err))


def _reset_to_form(message: str) -> None:
    """Return to the New Consultation form and show a clear notice."""
    st.session_state["form_notice"] = message
    st.session_state["consult_submitted"] = False
    st.session_state.pop("consult_results", None)
    st.session_state.pop("active_consultation_id", None)
    st.session_state.pop("consult_form_data", None)
    for key in ("consult_business_idea", "consult_tech_preference",
                "consult_cloud_preference", "consult_timeline",
                "consult_daily_traffic", "consult_country"):
        st.session_state.pop(key, None)
    st.rerun()


def _render_agent_output(agent_key: str, data: dict, expanded: bool = True) -> None:
    """Route the rendering to specialized components based on the agent type."""
    if not data or (len(data) == 1 and "raw" in data):
        st.markdown(data.get("raw", "_No structured output._"))
        return

    if agent_key == "business_analysis":
        _render_business_analysis(data)
    elif agent_key == "solution_architecture":
        _render_solution_architecture(data)
    elif agent_key == "technology_recommendation":
        _render_technology_recommendation(data)
    elif agent_key == "delivery_plan":
        _render_delivery_plan(data)
    else:
        # Fallback for unknown agent keys
        for k, v in data.items():
            st.write(f"**{k}**: {v}")


def _esc(value) -> str:
    """HTML-escape any dynamic value before it goes into unsafe HTML."""
    return html.escape("" if value is None else str(value), quote=True)


def _card(title: str, body_html: str) -> None:
    """Render a compact branded card with a title and HTML body."""
    st.markdown(
        f"""<div class="sf-card" style="padding:1rem 1.2rem; margin-bottom:0.7rem;">
            <div class="sf-card-title" style="margin-bottom:0.5rem; font-size:0.88rem;">{_esc(title)}</div>
            <div style="font-size:0.84rem; line-height:1.5; color:var(--sf-text);">{body_html}</div>
        </div>""",
        unsafe_allow_html=True,
    )


def _list_to_html(items: list, compact: bool = True) -> str:
    """Convert a list of strings or dicts into compact (escaped) HTML."""
    if not items:
        return "<em>None</em>"
    parts = []
    for item in items:
        if isinstance(item, dict):
            inner = " · ".join(
                f"<strong>{_esc(k.replace('_', ' ').title())}:</strong> {_esc(v)}"
                for k, v in item.items()
            )
            parts.append(f"<li style='margin-bottom:2px;'>{inner}</li>")
        else:
            parts.append(f"<li style='margin-bottom:2px;'>{_esc(item)}</li>")
    pad = "margin:0; padding-left:1.2rem;" if compact else "padding-left:1.2rem;"
    return f"<ul style='{pad}'>{''.join(parts)}</ul>"


def _render_generic_remaining(data: dict, handled_keys: set) -> None:
    """Render any fields that weren't explicitly formatted above as cards."""
    remaining = {k: v for k, v in data.items() if k not in handled_keys and v}
    if not remaining:
        return
    cards_html = []
    for key, value in remaining.items():
        title = key.replace("_", " ").title()
        if isinstance(value, list):
            body = _list_to_html(value)
        elif isinstance(value, dict):
            body = _list_to_html([f"<strong>{_esc(k.replace('_', ' ').title())}:</strong> {_esc(v)}" for k, v in value.items()])
        else:
            body = _esc(value)
        cards_html.append((title, body))

    # Render in 2-column rows
    for i in range(0, len(cards_html), 2):
        cols = st.columns(2)
        for j, col in enumerate(cols):
            if i + j < len(cards_html):
                with col:
                    _card(cards_html[i + j][0], cards_html[i + j][1])


def _render_business_analysis(data: dict) -> None:
    handled = {"problem_statement", "users", "mvp_scope", "risks"}

    problem = data.get("problem_statement", "")
    if problem:
        _card("📋 Problem Statement", f"<p style='margin:0;'>{_esc(problem)}</p>")

    c1, c2, c3 = st.columns(3)
    with c1:
        _card("👥 Users", _list_to_html(data.get("users", [])))
    with c2:
        _card("🎯 MVP Scope", _list_to_html(data.get("mvp_scope", [])))
    with c3:
        _card("⚠️ Risks", _list_to_html(data.get("risks", [])))

    _render_generic_remaining(data, handled)


def _render_solution_architecture(data: dict) -> None:
    handled = {"architecture_style", "components", "data_flow"}

    style = data.get("architecture_style", "")
    if style:
        _card("🏗️ Architecture Style",
              f"<div style='font-size:0.95rem; font-weight:700; color:var(--sf-navy); "
              f"background:var(--sf-blue-light); border:1px solid var(--sf-border); "
              f"border-radius:10px; padding:0.7rem 1rem; display:inline-block;'>{_esc(style)}</div>")

    c1, c2 = st.columns(2)
    comps = data.get("components", [])
    comp_html = ""
    for comp in comps:
        if isinstance(comp, dict):
            comp_html += f"<li style='margin-bottom:3px;'><strong>{_esc(comp.get('name', ''))}</strong>: {_esc(comp.get('description', ''))}</li>"
        else:
            comp_html += f"<li style='margin-bottom:3px;'>{_esc(comp)}</li>"
    with c1:
        _card("🧩 Components", f"<ul style='margin:0; padding-left:1.2rem;'>{comp_html}</ul>")

    flows = data.get("data_flow", [])
    if flows:
        flow_html = ""
        for i, flow in enumerate(flows, 1):
            flow_html += f"<li style='margin-bottom:3px;'>{_esc(flow)}</li>"
        with c2:
            _card("🔄 Data Flow", f"<ol style='margin:0; padding-left:1.2rem;'>{flow_html}</ol>")

    _render_generic_remaining(data, handled)


def _render_technology_recommendation(data: dict) -> None:
    handled = {"cloud", "technologies"}

    cloud = data.get("cloud", {})
    if isinstance(cloud, dict) and cloud:
        services = ", ".join(_esc(s) if s is not None else "" for s in cloud.get("services", []))
        _card("☁️ Cloud Provider",
              f"<strong>{_esc(cloud.get('provider', 'N/A'))}</strong>"
              f"<br><small style='color:var(--sf-text-muted);'>Services: {services}</small>")

    techs = data.get("technologies", [])
    if techs:
        rows = ""
        for tech in techs:
            if isinstance(tech, dict):
                rows += (f"<tr><td style='padding:4px 8px;'><strong>{_esc(tech.get('category', ''))}</strong></td>"
                         f"<td style='padding:4px 8px;'>{_esc(tech.get('technology', ''))}</td>"
                         f"<td style='padding:4px 8px; color:var(--sf-text-muted); font-size:0.8rem;'>{_esc(tech.get('reason', ''))}</td></tr>")
            else:
                rows += f"<tr><td style='padding:4px 8px;' colspan='3'>{_esc(tech)}</td></tr>"
        table = (f"<table style='width:100%; border-collapse:collapse; font-size:0.84rem;'>"
                 f"<tr style='border-bottom:1px solid var(--sf-border);'>"
                 f"<th style='padding:4px 8px; text-align:left;'>Category</th>"
                 f"<th style='padding:4px 8px; text-align:left;'>Technology</th>"
                 f"<th style='padding:4px 8px; text-align:left;'>Reason</th></tr>{rows}</table>")
        _card("🛠️ Recommended Stack", table)

    _render_generic_remaining(data, handled)


def _render_delivery_plan(data: dict) -> None:
    handled = {"timeline", "team_roles"}

    c1, c2 = st.columns([2, 1])

    timeline = data.get("timeline", [])
    if timeline:
        rows = ""
        for p in timeline:
            if isinstance(p, dict):
                rows += (f"<tr><td style='padding:4px 8px;'>{_esc(p.get('phase',''))}</td>"
                         f"<td style='padding:4px 8px;'>{_esc(p.get('duration_weeks',''))} wks</td></tr>")
            else:
                rows += f"<tr><td style='padding:4px 8px;' colspan='2'>{_esc(p)}</td></tr>"
        table = (f"<table style='width:100%; border-collapse:collapse; font-size:0.84rem;'>"
                 f"<tr style='border-bottom:1px solid var(--sf-border);'>"
                 f"<th style='padding:4px 8px; text-align:left;'>Phase</th>"
                 f"<th style='padding:4px 8px; text-align:left;'>Duration</th></tr>{rows}</table>")
        with c1:
            _card("📅 Timeline", table)

    roles = data.get("team_roles") or data.get("team", [])
    role_items = []
    for role in roles:
        if isinstance(role, dict):
            role_items.append(f"{_esc(role.get('count', '?'))}× {_esc(role.get('role', ''))}")
        else:
            role_items.append(_esc(str(role)))
    with c2:
        _card("👥 Team Roles", _list_to_html(role_items))

    _render_generic_remaining(data, handled)


def _render_saved_results() -> None:
    """Re-render a completed consultation from session state.

    Called on Streamlit reruns after the pipeline already finished, so we
    don't POST /consultations again (which used to create duplicate docs).
    """
    saved = st.session_state["consult_results"]
    agent_results = saved.get("agent_results") or {}
    agent_statuses = saved.get("agent_statuses") or {}
    status_label = saved.get("status_label")

    if status_label == "completed":
        st.success("🎉 **All agents finished!** Your solution blueprint is ready. Click the tabs above to view details.")
    else:
        st.info("Consultation in progress…")

    consultation_id = st.session_state.get("active_consultation_id")
    if consultation_id:
        st.markdown("")
        try:
            html_report = api_client.export_blueprint_html(
                token=st.session_state["auth_token"],
                consultation_id=consultation_id,
            )
            st.download_button(
                "📥 Download Blueprint (HTML)",
                data=html_report,
                file_name="blueprint.html",
                mime="text/html",
                type="primary",
            )
        except ApiError as dlerr:
            st.warning(f"Blueprint ready, but download failed: {dlerr}")

    tabs = st.tabs([
        "Business Analyst",
        "Solution Architect",
        "Technology Advisor",
        "Delivery Planner",
    ])
    for idx, key in enumerate(AGENT_ORDER):
        with tabs[idx]:
            if key in agent_results:
                _render_agent_output(key, agent_results[key])
            else:
                st.info("No output for this agent yet.")

