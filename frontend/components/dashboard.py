from typing import Any, Dict

import streamlit as st

from frontend.components.score_display import display_overall_score, display_score_breakdown
from frontend.components.strengths_issues import display_strengths, display_critical_issues
from frontend.components.skill_validation import display_skill_validation
from frontend.components.jd_comparison import display_jd_comparison
from frontend.components.detailed_feedback import display_detailed_feedback
from frontend.components.action_items import display_action_items
from frontend.components.recommendations import display_recommendations, display_resume_suggestions


def display_results_dashboard(analysis: Dict[str, Any]) -> None:
    """
    Render the full results page from one backend response dict.

    `analysis` is the JSON body returned by POST /api/v1/analyze-resume
    (i.e. an AnalysisResponse). No transformation is done here — every
    section reads the fields it needs directly.
    """
    display_overall_score(analysis)
    st.markdown("---")

    display_score_breakdown(analysis)

    with st.expander("Critical issues"):
        display_critical_issues(analysis)

    with st.expander("Skill validation"):
        display_skill_validation(analysis)

    with st.expander("Strengths"):
        display_strengths(analysis.get("strengths") or [])

    # JD comparison only shows up if the user actually submitted a JD.
    jd_comparison = analysis.get("jd_comparison") or analysis.get("jd_match_analysis")
    if jd_comparison:
        with st.expander("Job description match"):
            display_jd_comparison(jd_comparison, analysis.get("skill_validation_details") or {})

    with st.expander("Areas to improve"):
        display_detailed_feedback(analysis)
    with st.expander("Action checklist"):
        display_action_items(analysis)
    with st.expander("Resume improvement suggestions"):
        display_resume_suggestions(analysis)
    with st.expander("Projects recommended for you"):
        display_recommendations(analysis)
