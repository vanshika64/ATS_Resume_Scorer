from typing import Optional

import requests
import streamlit as st

from frontend.services import api_client
from frontend.components.dashboard import display_results_dashboard


def _read_jd(jd_file, jd_text: str) -> str:
    if jd_text:
        return jd_text.strip()
    if jd_file is None:
        return ""
    if jd_file.name.lower().endswith(".txt"):
        return jd_file.getvalue().decode("utf-8", errors="ignore")
    st.warning("Job descriptions can be pasted as text or uploaded as a .txt file.")
    return ""


def _show_backend_error(exc: Exception) -> None:
    if isinstance(exc, requests.ConnectionError):
        st.error("Could not reach the analysis service. Check that the backend is running.")
    elif isinstance(exc, requests.Timeout):
        st.error("The analysis service took too long to respond. Try again or check the backend logs.")
    elif isinstance(exc, requests.HTTPError) and exc.response is not None:
        try:
            detail = exc.response.json().get("detail", exc.response.text)
        except ValueError:
            detail = exc.response.text
        st.error(f"Backend returned {exc.response.status_code}: {detail}")
    else:
        st.error(f"Unexpected error: {exc}")


def _summary_text(analysis: dict) -> str:
    score = float(analysis.get("ATS_score", analysis.get("ats_score", 0)) or 0)
    lines = [f"ATS Score: {score:.0f}/100", ""]
    if analysis.get("strengths"):
        lines.extend(("STRENGTHS:", *(f"  - {item}" for item in analysis["strengths"]), ""))
    if analysis.get("critical_issues"):
        lines.extend(("CRITICAL ISSUES:", *(f"  - {item}" for item in analysis["critical_issues"]), ""))
    if analysis.get("suggestions"):
        lines.extend(("SUGGESTIONS:", *(f"  - {item}" for item in analysis["suggestions"])))
    return "\n".join(lines)


def _render_upload_area(analysis_mode: str):
    left, right = st.columns(2, gap="large")
    with left:
        st.markdown("<h3 class='upload-panel-title'>Resume document</h3><p class='upload-help'>PDF, DOC, or DOCX · Maximum 5 MB</p>", unsafe_allow_html=True)
        resume_file = st.file_uploader(
            "Choose a resume file", type=["pdf", "doc", "docx"],
            help="Supported formats: PDF, DOC and DOCX. Maximum file size: 5 MB.",
            key="resume_upload", label_visibility="collapsed",
        )
        if resume_file:
            st.success(f"Ready to analyze: {resume_file.name} · {resume_file.size / 1024:.1f} KB")

    jd_file: Optional[object] = None
    jd_text = ""
    with right:
        st.markdown("<h3 class='upload-panel-title'>Job description</h3><p class='upload-help'>Optional for general scoring; needed for a role-specific match.</p>", unsafe_allow_html=True)
        if analysis_mode == "Job Description Comparison":
            jd_method = st.radio("Job description input", ["Paste text", "Upload .txt"], horizontal=True, key="jd_input_method", label_visibility="collapsed")
            if jd_method == "Upload .txt":
                jd_file = st.file_uploader("Choose job description file", type=["txt"], key="jd_upload")
                if jd_file:
                    st.success(f"Ready to compare: {jd_file.name}")
            else:
                jd_text = st.text_area("Paste the job description", height=180, placeholder="Paste the role responsibilities and requirements here...", key="jd_text")
        else:
            st.markdown("<div class='status-note'>Select Job Description Comparison to add target-role requirements.</div>", unsafe_allow_html=True)
    return resume_file, jd_file, jd_text


def _render_export_buttons(analysis: dict) -> None:
    st.markdown("## Export your analysis")
    pdf_col, text_col = st.columns(2)
    with pdf_col:
        if st.button("Generate PDF report", use_container_width=True, type="primary", key="generate_pdf_button"):
            try:
                with st.spinner("Preparing the report..."):
                    pdf_bytes = api_client.generate_pdf(analysis, access_token=st.session_state["access_token"])
                st.session_state["scorer_pdf_bytes"] = pdf_bytes
            except requests.RequestException as exc:
                _show_backend_error(exc)
        if "scorer_pdf_bytes" in st.session_state:
            st.download_button("Download PDF", data=st.session_state["scorer_pdf_bytes"], file_name="ats_resume_report.pdf", mime="application/pdf", use_container_width=True, key="download_pdf_report")
    with text_col:
        st.download_button("Download text summary", data=_summary_text(analysis), file_name="ats_summary.txt", mime="text/plain", use_container_width=True, key="download_summary")


def render() -> None:
    st.markdown("<div class='page-kicker'>Resume analysis</div>", unsafe_allow_html=True)
    st.title("ATS Scorer")
    st.markdown("<p class='page-copy'>Upload a resume to see its strengths, evidence gaps and concrete opportunities to improve.</p>", unsafe_allow_html=True)

    st.markdown("## Choose an analysis mode")
    analysis_mode = st.radio(
        "Analysis mode",
        ["General ATS Score", "Job Description Comparison"],
        horizontal=True,
        label_visibility="collapsed",
        key="analysis_mode",
    )
    target_role = st.text_input("Target role for project recommendations", placeholder="For example, Backend Developer", key="target_role_input")

    st.markdown("## Add your documents")
    resume_file, jd_file, jd_text = _render_upload_area(analysis_mode)

    access_token = st.session_state.get("access_token")
    if not access_token:
        st.info("Sign in to run an analysis and save it to your history.")
        if st.session_state.get("scorer_analysis"):
            display_results_dashboard(st.session_state["scorer_analysis"])
        return

    if not resume_file:
        st.markdown("<div class='status-note'>Choose a resume to start your analysis.</div>", unsafe_allow_html=True)
        if st.session_state.get("scorer_analysis"):
            display_results_dashboard(st.session_state["scorer_analysis"])
            _render_export_buttons(st.session_state["scorer_analysis"])
        return

    if st.button("Analyze resume", use_container_width=True, type="primary", key="analyze_resume_button"):
        st.session_state.pop("scorer_pdf_bytes", None)
        st.session_state.pop("scorer_analysis", None)
        job_description = _read_jd(jd_file, jd_text) if analysis_mode == "Job Description Comparison" else ""
        if analysis_mode == "Job Description Comparison" and not job_description.strip():
            st.warning("Add a job description or switch to General ATS Score.")
            return
        try:
            with st.spinner("Analyzing your resume. This may take a little while..."):
                analysis = api_client.analyze_resume(
                    resume_file=resume_file,
                    access_token=access_token,
                    job_description=job_description,
                    target_role=target_role.strip(),
                )
        except requests.RequestException as exc:
            _show_backend_error(exc)
            return

        st.session_state["scorer_analysis"] = analysis
        st.markdown("<div class='status-note success'>Analysis complete</div>", unsafe_allow_html=True)
        display_results_dashboard(analysis)
        _render_export_buttons(analysis)
        return

    if st.session_state.get("scorer_analysis"):
        display_results_dashboard(st.session_state["scorer_analysis"])
        _render_export_buttons(st.session_state["scorer_analysis"])
