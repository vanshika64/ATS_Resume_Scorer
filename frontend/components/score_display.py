from typing import Any, Dict

import streamlit as st

from frontend.components._helpers import get_score_emoji


# Component max scores match backend/core/config.py SCORE_WEIGHTS.
# (Backend returns each component's score on its own scale, not 0–100.)
COMPONENTS = [
    ("Formatting",        "formatting",        20, "->"),
    ("Keywords & Skills", "keywords",          25, "->"),
    ("Content Quality",   "content",           25, "->"),
    ("Skill Validation",  "skill_validation",  15, "->"),
    ("ATS Compatibility", "ats_compatibility", 15, "->"),
]


def display_overall_score(analysis: Dict[str, Any]) -> None:
    """Big colored score card with a short interpretation line."""
    score = float(analysis.get("ATS_score", analysis.get("ats_score", 0)))
    interpretation = analysis.get("interpretation", "")
    score_tone = "excellent" if score >= 80 else "good" if score >= 60 else "needs"
    emoji = get_score_emoji(score)

    st.markdown("##  Analysis Results")
    _, mid, _ = st.columns([1, 2, 1])
    with mid:
        st.markdown(
            f"""
            <div class="score-card">
                <h1 class="score-card-value score-tone-{score_tone}">
                    {emoji} {score:.0f}
                </h1>
                <h3 class="score-card-title">Overall ATS Score</h3>
                <p class="score-card-copy">{interpretation}</p>
            </div>
            """,
            unsafe_allow_html=True,
        )


def display_score_breakdown(analysis: Dict[str, Any]) -> None:
    """Five progress bars, one per scoring component."""
    component_scores = analysis.get("component_scores") or {}
    st.markdown("###  Score Breakdown")

    left, right = st.columns(2)
    for i, (label, key, max_score, icon) in enumerate(COMPONENTS):
        value = float(component_scores.get(key, 0))
        percentage = value / max_score if max_score else 0
        bar_tone = "is-good" if percentage >= 0.8 else "is-warning" if percentage >= 0.6 else "is-poor"

        with left if i % 2 == 0 else right:
            st.markdown(f"**{icon} {label}**")
            st.markdown(
                f"""
                <progress class="score-breakdown-progress {bar_tone}" max="1" value="{percentage}"></progress>
                """,
                unsafe_allow_html=True,
            )
            st.markdown(f"**{value:.0f}/{max_score}**")
            st.markdown("")
