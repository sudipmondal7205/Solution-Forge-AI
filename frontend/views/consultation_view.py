"""
views/consultation_view.py
===========================
"New Consultation" page — matches the mockup: business idea textarea,
technology preference, cloud preference, expected daily traffic, delivery
timeline slider, country search-select, and a "Generate Solution Blueprint"
submit button.

On successful submit, this creates the consultation via the backend and
routes the user to the Live Results page to watch the 4 agents run.
"""

import streamlit as st

import api_client
import config
import session_state as ss
import styles
from api_client import ApiError
from models import UserInput
from validators import validate_consultation_form


def render() -> None:
    styles.page_header("New Consultation")

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
            min_value=0, step=100, value=0,
            key="consult_daily_traffic",
            help="Approximate number of daily active users / requests.",
        )
        data_hosting_country = st.selectbox(
            "Country",
            options=[""] + config.COUNTRY_OPTIONS,
            key="consult_country",
            format_func=lambda c: "Search a country..." if c == "" else c,
        )

    st.write("")
    if st.button("🚀  Generate Solution Blueprint", key="consult_submit",
                 type="primary", use_container_width=True):
        _submit(
            business_idea=business_idea,
            technology_preference=technology_preference,
            cloud_preference=cloud_preference,
            expected_daily_traffic=expected_daily_traffic,
            delivery_timeline_months=delivery_timeline_months,
            data_hosting_country=data_hosting_country,
        )


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

    try:
        with st.spinner("Kicking off your AI consulting team..."):
            response = api_client.create_consultation(
                token=st.session_state["auth_token"],
                user_input=user_input.to_dict(),
            )
        st.session_state["active_consultation_id"] = response.get("consultation_id")
        st.session_state["viewing_consultation_id"] = response.get("consultation_id")
        st.session_state["consultation_summary"] = {
            "business_idea": user_input.business_idea,
            "expected_daily_traffic": user_input.expected_daily_traffic,
            "delivery_timeline_months": user_input.delivery_timeline_months,
            "cloud_preference": user_input.cloud_preference,
            "data_hosting_country": user_input.data_hosting_country,
        }
        ss.go_to("live_results")
        st.rerun()
    except ApiError as err:
        st.error(str(err))
