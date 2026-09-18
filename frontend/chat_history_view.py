"""
views/chat_history_view.py
===========================
"Chat History" page — matches the mockup: a list of past consultations,
each with Title / Date / Cloud Preference / Status, and View Blueprint /
Export PDF actions.
"""

import streamlit as st

import api_client
import session_state as ss
import styles
from api_client import ApiError


def render() -> None:
    styles.page_header("Chat History")

    try:
        history = api_client.get_consultation_history(token=st.session_state["auth_token"])
    except ApiError as err:
        st.error(str(err))
        return

    if not history:
        st.info("You haven't run any consultations yet. Start one from **New Consultation**.")
        return

    for entry in history:
        _render_history_row(entry)


def _render_history_row(entry: dict) -> None:
    st.markdown('<div class="sf-card sf-hover">', unsafe_allow_html=True)
    col_title, col_date, col_cloud, col_status, col_view, col_export = st.columns(
        [3, 1.4, 1.4, 1.6, 1.2, 1.2]
    )

    with col_title:
        st.markdown("**Title**")
        st.write(entry.get("title", ""))
    with col_date:
        st.markdown("**Date**")
        st.write(entry.get("date", ""))
    with col_cloud:
        st.markdown("**Cloud Preference**")
        st.write(entry.get("cloud_preference", "—"))
    with col_status:
        st.markdown("**Status**")
        status_label = entry.get("status", "Processing")
        badge_class = styles.status_badge_class(status_label)
        st.markdown(f'<span class="sf-badge {badge_class}">{status_label}</span>', unsafe_allow_html=True)
    with col_view:
        st.write("")
        if st.button("View Blueprint", key=f"view_{entry.get('consultation_id')}", use_container_width=True):
            st.session_state["viewing_consultation_id"] = entry.get("consultation_id")
            ss.go_to("live_results")
            st.rerun()
    with col_export:
        st.write("")
        if st.button("Export PDF", key=f"export_{entry.get('consultation_id')}", use_container_width=True):
            st.info("PDF export will be available once the backend export endpoint is connected.")

    st.markdown("</div>", unsafe_allow_html=True)
