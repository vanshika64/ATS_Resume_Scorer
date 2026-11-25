from typing import Any, Dict, List

import streamlit as st


SEVERITY_ORDER = ("critical", "high", "moderate", "medium", "low", "info")


def _group_issues(issues: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    grouped: Dict[str, List[Dict[str, Any]]] = {level: [] for level in SEVERITY_ORDER}
    for issue in issues:
        level = str(issue.get("severity_level") or "low").lower()
        grouped.setdefault(level, []).append(issue)
    return grouped


def display_detailed_feedback(analysis: Dict[str, Any]) -> None:
    issues = [item for item in (analysis.get("detailed_feedback") or []) if isinstance(item, dict)]
    if not issues:
        st.info("No additional improvement items were returned for this analysis.")
        return

    st.caption(f"{len(issues)} item(s) from the resume review. Each recommendation should be checked against your actual experience.")
    grouped = _group_issues(issues)
    for level in SEVERITY_ORDER:
        items = grouped.get(level, [])
        if not items:
            continue
        label = "High priority" if level in {"critical", "high"} else "Medium priority" if level in {"moderate", "medium"} else "Polish"
        st.markdown(f"### {label} · {len(items)}")
        for issue in items:
            title = issue.get("issue_title", "Resume feedback")
            with st.container(border=True):
                st.markdown(f"**{title}**")
                if issue.get("explanation"):
                    st.write(issue["explanation"])
                if issue.get("where_it_appears"):
                    st.markdown("**Evidence or location**")
                    st.write(issue["where_it_appears"])
                if issue.get("how_to_fix"):
                    st.markdown("**Suggested improvement**")
                    st.write(issue["how_to_fix"])
                if issue.get("example_improvement"):
                    st.markdown("**Example structure**")
                    st.code(issue["example_improvement"], language=None)
