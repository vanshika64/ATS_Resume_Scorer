from html import escape
from typing import Any, Dict, Optional

import streamlit as st


def display_jd_comparison(jd_comparison: Optional[Dict[str, Any]], skill_validation: Optional[Dict[str, Any]] = None) -> None:
    if not jd_comparison:
        return

    match_pct = float(jd_comparison.get("match_percentage", 0) or 0)
    semantic = float(jd_comparison.get("semantic_similarity", 0) or 0)
    matched = jd_comparison.get("matched_keywords", []) or []
    missing = jd_comparison.get("missing_keywords", []) or []
    gaps = jd_comparison.get("skills_gap", []) or []

    left, right, third = st.columns(3)
    left.metric("Overall match", f"{match_pct:.0f}%")
    right.metric("Semantic similarity", f"{semantic * 100:.0f}%")
    third.metric("Requirements to review", len(gaps))

    st.markdown("### Matched requirements")
    if matched:
        st.markdown(" ".join(f"<span class='skill-chip demonstrated'>{escape(str(term))}</span>" for term in matched[:30]), unsafe_allow_html=True)
    else:
        st.caption("No matching job-description terms were identified.")

    gaps_col, missing_col = st.columns(2)
    with gaps_col:
        st.markdown("### Skill gaps")
        if gaps:
            for skill in gaps[:20]:
                st.markdown(f"- {skill}")
        else:
            st.caption("No skill gaps were identified by the comparison.")
    with missing_col:
        st.markdown("### Missing keywords")
        if missing:
            for term in missing[:20]:
                st.markdown(f"- {term}")
        else:
            st.caption("No missing keywords were returned.")

    evidence = (skill_validation or {}).get("skills", []) or []
    demonstrated = [item for item in evidence if item.get("classification") == "Demonstrated" and item.get("evidence")]
    if demonstrated:
        st.markdown("### Evidence from your resume")
        for item in demonstrated:
            with st.container(border=True):
                st.markdown(f"**{item.get('skill', 'Skill')} · {item.get('source_section', 'Resume')}**")
                if item.get("source_name"):
                    st.caption(item["source_name"])
                st.write(f"“{item['evidence']}”")
                st.write(item.get("explanation", ""))
    st.caption("Only the match score, matched terms, missing terms and skill gaps returned by the analysis are shown here.")
