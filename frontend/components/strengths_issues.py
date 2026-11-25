from html import escape
from typing import Any, Dict, List

import streamlit as st


def display_strengths(strengths: List[str]) -> None:
    if not strengths:
        st.info("No specific strengths were returned for this analysis.")
        return
    left, right = st.columns(2)
    for index, item in enumerate(strengths):
        with left if index % 2 == 0 else right:
            st.markdown(f"<article class='feedback-issue is-low'>{escape(str(item))}</article>", unsafe_allow_html=True)


def display_critical_issues(analysis: Dict[str, Any]) -> None:
    critical_titles = list(analysis.get("critical_issues") or [])
    feedback = analysis.get("detailed_feedback") or []
    lookup = {item.get("issue_title"): item for item in feedback if isinstance(item, dict)}
    structured_critical = [
        item for item in feedback
        if isinstance(item, dict) and str(item.get("severity_level", "")).lower() in {"critical", "high"}
    ]
    seen = set(critical_titles)
    critical_titles.extend(
        item.get("issue_title") for item in structured_critical
        if item.get("issue_title") and item.get("issue_title") not in seen
    )
    if not critical_titles:
        st.success("No critical issues were identified.")
        return
    st.caption("Review the highest-impact items first. Open an issue for its evidence and suggested correction.")
    for title in critical_titles:
        issue = lookup.get(title, {})
        severity = str(issue.get("severity_level", "High"))
        with st.container(border=True):
            st.markdown(f"**{title} · {severity.title()}**")
            if issue.get("explanation"):
                st.write(issue["explanation"])
            if issue.get("where_it_appears"):
                st.markdown("**Resume evidence or location**")
                st.write(issue["where_it_appears"])
            if issue.get("how_to_fix"):
                st.markdown("**Recommended improvement**")
                st.write(issue["how_to_fix"])
            if issue.get("action_items"):
                for action in issue["action_items"]:
                    st.markdown(f"- {action}")
