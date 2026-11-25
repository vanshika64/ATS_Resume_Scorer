from typing import Any, Dict, List, Tuple

import streamlit as st


PRIORITY_RANK = {"critical": 0, "high": 0, "moderate": 1, "medium": 1, "low": 2, "info": 2}
PRIORITY_LABEL = {0: "High priority", 1: "Medium priority", 2: "Low priority"}


def _collect_action_items(analysis: Dict[str, Any]) -> List[Tuple[int, str, str]]:
    items: List[Tuple[int, str, str]] = []
    for issue in analysis.get("detailed_feedback") or []:
        if not isinstance(issue, dict):
            continue
        level = str(issue.get("severity_level") or "low").lower()
        priority = PRIORITY_RANK.get(level, 2)
        for action in issue.get("action_items") or []:
            items.append((priority, str(issue.get("issue_title", "Resume improvement")), str(action)))
    if not items:
        items.extend((1, "Suggested improvement", str(item)) for item in analysis.get("suggestions") or [])
    return sorted(items, key=lambda row: row[0])


def display_action_items(analysis: Dict[str, Any]) -> None:
    items = _collect_action_items(analysis)
    if not items:
        st.info("No action items were returned for this analysis.")
        return
    st.caption("Work through the items that apply to your experience. Keep claims and metrics verifiable.")
    for priority in (0, 1, 2):
        group = [item for item in items if item[0] == priority]
        if not group:
            continue
        st.markdown(f"### {PRIORITY_LABEL[priority]}")
        for index, (_, source, action) in enumerate(group):
            with st.container(border=True):
                st.checkbox(action, key=f"action_item_{priority}_{index}_{abs(hash(source))}")
                st.caption(f"From: {source}")
