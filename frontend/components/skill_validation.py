from html import escape
from typing import Any, Dict, List

import streamlit as st


CLASSIFICATIONS = ("Demonstrated", "Weak Evidence", "Listed Only", "Not Found")


def _legacy_entries(details: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Keep old Supabase analyses readable after the response schema update."""
    entries = []
    for value in details.get("validated", []) or []:
        if isinstance(value, dict):
            entries.append({"skill": value.get("skill", ""), "classification": "Demonstrated", "source_section": "Project or Experience", "source_name": ", ".join(value.get("projects", []) or []), "evidence": "", "explanation": "This skill matched a project or experience description in the previous analysis.", "similarity": value.get("similarity"), "recommendation": "Add a specific example sentence if you want to make this evidence easier to review."})
    for value in details.get("unvalidated", []) or []:
        entries.append({"skill": value, "classification": "Listed Only", "source_section": "Skills", "source_name": "Technical Skills", "evidence": "", "explanation": "The previous analysis did not identify supporting project or experience evidence.", "similarity": None, "recommendation": f"If accurate, add a project or experience example showing how you used {value}."})
    return entries


def display_skill_validation(analysis: Dict[str, Any]) -> None:
    details = analysis.get("skill_validation_details") or {}
    entries = details.get("skills") or _legacy_entries(details)
    counts = {classification: sum(1 for entry in entries if entry.get("classification") == classification) for classification in CLASSIFICATIONS}
    total = len(entries)
    pct = details.get("evidence_coverage_pct", details.get("validation_pct", 0.0))

    if not entries:
        st.info("No skills were extracted from the resume or target job description.")
        return

    cols = st.columns(5)
    cols[0].metric("Skills reviewed", total)
    for col, classification in zip(cols[1:], CLASSIFICATIONS):
        col.metric(classification, counts[classification])
    st.caption(f"Evidence coverage · {pct:.0f}%")
    st.progress(min(max(float(pct) / 100.0, 0.0), 1.0))

    for classification in CLASSIFICATIONS:
        matching = [str(entry.get("skill") or "Skill") for entry in entries if entry.get("classification") == classification]
        if not matching:
            continue
        preview = matching[:8]
        chip_class = {
            "Demonstrated": "demonstrated",
            "Weak Evidence": "weak",
            "Listed Only": "listed",
            "Not Found": "not-found",
        }[classification]
        chips = " ".join(
            f"<span class='skill-chip {chip_class}'>{escape(skill)}</span>"
            for skill in preview
        )
        st.markdown(f"**{classification}**  {chips}", unsafe_allow_html=True)
        if len(matching) > len(preview):
            st.caption(f"And {len(matching) - len(preview)} more")
