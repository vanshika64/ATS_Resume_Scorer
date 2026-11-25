import requests
import streamlit as st

from frontend.services import api_client


def _show_backend_error(exc: Exception) -> None:
    if isinstance(exc, requests.ConnectionError):
        st.error("Could not reach the analysis service. Check that the backend is running.")
    elif isinstance(exc, requests.HTTPError) and exc.response is not None:
        try:
            detail = exc.response.json().get("detail", exc.response.text)
        except ValueError:
            detail = exc.response.text
        st.error(f"Backend returned {exc.response.status_code}: {detail}")
    else:
        st.error(f"Unexpected error: {exc}")


def render() -> None:
    st.markdown("<div class='page-kicker'>Your workspace</div>", unsafe_allow_html=True)
    st.title("Analysis history")
    st.markdown("<p class='page-copy'>Review saved resume analyses, their scores and job-specific comparisons.</p>", unsafe_allow_html=True)

    access_token = st.session_state.get("access_token")
    if not access_token:
        st.warning("Sign in to view analyses saved to your account.")
        return

    try:
        history = api_client.get_history(access_token)
    except requests.RequestException as exc:
        _show_backend_error(exc)
        return

    if not history:
        with st.container(border=True):
            st.markdown("#### No saved analyses yet")
            st.write("Run an analysis to see its score breakdown and report here.")
            if st.button("Start an analysis", type="primary"):
                st.session_state.current_view = "scorer"
                st.rerun()
        return

    st.metric("Saved analyses", len(history))
    for index, entry in enumerate(history):
        filename = entry.get("filename", "Resume")
        score = float(entry.get("ats_score", 0) or 0)
        created_at = entry.get("created_at", "")
        analysis = entry.get("analysis_result", {}) or {}
        component_scores = analysis.get("component_scores", {}) or {}
        jd_match = analysis.get("jd_comparison") or analysis.get("jd_match_analysis")
        entry_id = str(entry.get("id", index))

        with st.expander(f"{filename} · {score:.0f}/100 · {created_at}"):
            st.markdown("#### Score breakdown")
            a, b, c, d, e, f = st.columns(6)
            a.metric("Overall", f"{score:.0f}/100")
            b.metric("Formatting", f"{float(component_scores.get('formatting', 0) or 0):.0f}/20")
            c.metric("Keywords", f"{float(component_scores.get('keywords', 0) or 0):.0f}/25")
            d.metric("Content", f"{float(component_scores.get('content', 0) or 0):.0f}/25")
            e.metric("Skills", f"{float(component_scores.get('skill_validation', 0) or 0):.0f}/15")
            f.metric("ATS", f"{float(component_scores.get('ats_compatibility', 0) or 0):.0f}/15")
            if jd_match:
                st.caption(f"Job description match: {float(jd_match.get('match_percentage', 0) or 0):.0f}%")

            pdf_key = f"history_pdf_{entry_id}"
            if st.button("Prepare PDF report", key=f"history_prepare_pdf_{index}"):
                try:
                    with st.spinner("Preparing the report..."):
                        st.session_state[pdf_key] = api_client.get_history_pdf(entry_id, access_token)
                except requests.RequestException as exc:
                    _show_backend_error(exc)
            if st.session_state.get(pdf_key):
                st.download_button("Download PDF", data=st.session_state[pdf_key], file_name=f"ats_report_{entry_id}.pdf", mime="application/pdf", key=f"history_download_pdf_{index}")

            if st.button("Delete analysis", key=f"delete_{index}"):
                try:
                    api_client.delete_history_entry(entry_id, access_token)
                    st.success("Analysis deleted.")
                    st.rerun()
                except requests.RequestException as exc:
                    _show_backend_error(exc)
