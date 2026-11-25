from typing import Any, Dict

import requests
import streamlit as st
from frontend.services import api_client


def display_recommendations(analysis: Dict[str, Any]) -> None:
    current_role = analysis.get("target_role", "")
    role = st.text_input("Target role", value=current_role, key="project_target_role")
    if st.button("Generate project plans", key="regenerate_project_recommendations"):
        token = st.session_state.get("access_token")
        if not token:
            st.warning("Sign in to generate personalized project plans.")
        else:
            try:
                with st.spinner("Creating role-focused project plans..."):
                    result = api_client.regenerate_project_recommendations(analysis, role, token)
                updated = dict(analysis)
                updated["target_role"] = result.get("target_role", role)
                updated["project_recommendations"] = result.get("recommendations", [])
                updated["recommendations_source"] = result.get("source", "")
                st.session_state["scorer_analysis"] = updated
                st.rerun()
            except requests.RequestException as exc:
                st.error(f"Could not generate project plans: {exc}")

    recommendations = analysis.get("project_recommendations") or []
    if not recommendations:
        st.info("Add a target role and generate project ideas tailored to your resume evidence.")
        return

    if analysis.get("recommendations_source") == "fallback":
        st.caption("Personalized from your resume and skill gaps using the built-in project planner.")
    for project in recommendations:
        title = project.get("title", "Recommended project")
        difficulty = project.get("difficulty", "Intermediate")
        with st.container(border=True):
            st.markdown(f"**{title} · {difficulty}**")
            st.write(project.get("description", ""))
            if project.get("relevance"):
                st.markdown("**Why it is recommended**")
                st.write(project["relevance"])
            for heading, key in (
                ("Skills to practice", "skills_demonstrated"),
                ("Skill gaps addressed", "skills_addressed"),
                ("Technologies", "technologies"),
                ("Core features", "core_features"),
                ("Implementation stages", "implementation_stages"),
            ):
                values = project.get(key) or []
                if values:
                    st.markdown(f"**{heading}**")
                    for value in values:
                        st.markdown(f"- {value}")
            if project.get("problem_solved"):
                st.markdown("**Problem it addresses**")
                st.write(project["problem_solved"])
            if project.get("resume_impact"):
                st.markdown("**Expected learning and resume value**")
                st.write(project["resume_impact"])
            if project.get("resume_bullet_structure"):
                st.markdown("**Resume bullet structure after completion**")
                st.code(project["resume_bullet_structure"], language=None)


def display_resume_suggestions(analysis: Dict[str, Any]) -> None:
    suggestions = analysis.get("suggestions") or []
    if not suggestions:
        st.info("No general resume improvement suggestions were returned for this analysis.")
        return
    for suggestion in suggestions:
        st.markdown(f"- {suggestion}")
