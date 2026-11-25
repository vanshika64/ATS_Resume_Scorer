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
    """Show the unchanged component scores with their scorer-derived explanations."""
    component_scores = analysis.get("component_scores") or {}
    explanations = {item.get("category"): item for item in analysis.get("score_explanations", []) if isinstance(item, dict)}
    if "Keywords and Skills" in explanations:
        explanations["Keywords & Skills"] = explanations["Keywords and Skills"]
    st.markdown("###  Score Breakdown")

    overall = analysis.get("overall_score_explanation") or {}
    if overall.get("strongest_category") or overall.get("weakest_category"):
        st.caption(f"Strongest area: **{overall.get('strongest_category', '—')}** ({overall.get('strongest_score', '—')}) · Area with most room to improve: **{overall.get('weakest_category', '—')}** ({overall.get('weakest_score', '—')}).")
    with st.expander("How the overall score is calculated"):
        st.write(overall.get("calculation", "The existing scoring model combines the five component scores and applies its existing bonuses and job-description penalties."))
        if overall.get("bonuses"):
            st.markdown("**Bonuses:** " + ", ".join(f"{name.replace('_', ' ')} (+{points:g})" for name, points in overall["bonuses"].items()))
        if overall.get("penalties"):
            st.markdown("**Penalties:** " + ", ".join(f"{name.replace('_', ' ')} (−{points:g})" for name, points in overall["penalties"].items()))

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
            detail = explanations.get(label)
            if detail:
                with st.expander(f"Why {value:.0f}/{max_score}?"):
                    st.write(detail.get("reason", ""))
                    deductions = detail.get("deductions") or []
                    if deductions:
                        st.markdown("**What affected the score**")
                        for deduction in deductions:
                            points = deduction.get("points")
                            suffix = f" (−{points:g} points)" if isinstance(points, (int, float)) and points else ""
                            st.markdown(f"- **{deduction.get('item', 'Scoring signal')}**{suffix}: {deduction.get('evidence', '')}")
                    if detail.get("missing_elements"):
                        st.markdown("**Missing elements**")
                        for item in detail["missing_elements"]:
                            st.markdown(f"- {item}")
                    if detail.get("suggestions"):
                        st.markdown("**Ways to improve**")
                        for item in detail["suggestions"]:
                            st.markdown(f"- {item}")
                    if detail.get("evidence"):
                        st.caption("Signals used: " + "; ".join(str(item) for item in detail["evidence"]))
