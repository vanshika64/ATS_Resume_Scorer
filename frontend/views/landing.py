import requests
import streamlit as st

from frontend.services import api_client


def _set_view(view: str) -> None:
    st.session_state.current_view = view
    st.rerun()


def _public_landing() -> None:
    st.markdown(
        """
        <section class="hero-panel" aria-labelledby="home-title">
          <div class="hero-eyebrow">A clearer way to apply</div>
          <h1 id="home-title" class="hero-title">Build a Resume That Proves Your Potential.</h1>
          <p class="hero-copy">Go beyond keyword matching. Understand your resume, validate your skills, identify gaps and discover projects that strengthen your career profile.</p>
        </section>
        """,
        unsafe_allow_html=True,
    )
    theme = st.session_state.get("theme", "dark")
    st.markdown(
        f"""
        <div class="home-cta-actions" aria-label="Account actions">
          <a class="home-cta home-cta-primary" href="?view=auth&amp;theme={theme}&amp;mode=signup">Create your account</a>
          <a class="home-cta" href="?view=auth&amp;theme={theme}&amp;mode=signin">Sign in</a>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("<div class='section-kicker'>A better way to prepare</div>", unsafe_allow_html=True)
    st.markdown("## Understand what your resume already shows")
    first, second, third = st.columns(3)
    cards = [
        ("<svg viewBox='0 0 24 24'><path d='M4 19V5m0 14h16M8 16v-4m4 4V7m4 9v-6'/></svg>", "Transparent ATS Analysis", "Understand exactly why your resume receives its score, with explanations tied to measurable scoring signals."),
        ("<svg viewBox='0 0 24 24'><path d='M5 12.5 9.3 17 19 7'/><path d='M12 3 4 6v6c0 4.5 3.4 7.4 8 9 4.6-1.6 8-4.5 8-9V6z'/></svg>", "Evidence-Based Skill Validation", "See which skills your projects and experience demonstrate, and which are only listed."),
        ("<svg viewBox='0 0 24 24'><path d='M12 3v4m0 10v4M3 12h4m10 0h4M5.6 5.6l2.8 2.8m7.2 7.2 2.8 2.8m0-12.8-2.8 2.8m-7.2 7.2-2.8 2.8'/><circle cx='12' cy='12' r='3'/></svg>", "Personalized Project Recommendations", "Explore practical projects based on your target role and the gaps in your resume."),
    ]
    for column, (icon, title, copy) in zip((first, second, third), cards):
        with column:
            st.markdown(f"<article class='feature-card'><div class='feature-mark' aria-hidden='true'>{icon}</div><h3>{title}</h3><p>{copy}</p></article>", unsafe_allow_html=True)


def _signed_in_dashboard() -> None:
    email = st.session_state.get("user_email") or "there"
    name = email.split("@", 1)[0].replace(".", " ").replace("_", " ").title() if "@" in email else email
    st.markdown("<div class='page-kicker'>Your workspace</div>", unsafe_allow_html=True)
    st.title(f"Welcome back, {name}")
    st.markdown("<p class='page-copy'>Analyze your resume, understand your strengths and discover opportunities to improve.</p>", unsafe_allow_html=True)

    history = []
    try:
        history = api_client.get_history(st.session_state.access_token)
    except requests.RequestException:
        # The dashboard actions stay available even if the history service is offline.
        pass

    if history:
        latest = history[0].get("analysis_result", {}) or {}
        skill_details = latest.get("skill_validation_details", {}) or {}
        validated = skill_details.get("validated_count")
        if validated is None:
            validated = len(skill_details.get("validated", []) or [])
        m1, m2, m3 = st.columns(3)
        m1.metric("Resumes analyzed", len(history))
        m2.metric("Most recent ATS score", f"{float(history[0].get('ats_score', 0)):.0f}/100")
        m3.metric("Validated skills in latest analysis", validated)

    left, right = st.columns(2)
    with left:
        with st.container(border=True):
            st.markdown("#### Start a new analysis")
            st.write("Upload a resume and get an explainable ATS review.")
            if st.button("Start new analysis", type="primary", use_container_width=True):
                _set_view("scorer")
    with right:
        with st.container(border=True):
            st.markdown("#### Review your past work")
            st.write("Open saved analyses and revisit your score breakdowns.")
            if st.button("View previous analyses", use_container_width=True):
                _set_view("history")

    if history:
        st.markdown("<div class='section-kicker'>Recent activity</div>", unsafe_allow_html=True)
        st.markdown("## Recent analyses")
        for index, entry in enumerate(history[:3]):
            filename = entry.get("filename", "Resume analysis")
            score = float(entry.get("ats_score", 0))
            created = entry.get("created_at", "")
            with st.expander(f"{filename} · {score:.0f}/100 · {created}"):
                if st.button("Open analysis history", key=f"recent_analysis_{index}"):
                    _set_view("history")


def render() -> None:
    if st.session_state.get("access_token"):
        _signed_in_dashboard()
    else:
        _public_landing()
