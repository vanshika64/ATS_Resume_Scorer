import streamlit as st


def render() -> None:
    """Render the product landing page."""

    st.markdown("""
    <div class="hero-panel">
        <div class="hero-eyebrow">Smarter job applications</div>
        <h1 class="hero-title">Put your best resume forward.</h1>
        <p class="hero-copy">
            Get clear, practical feedback on your resume's ATS compatibility
            and focus your next edit where it matters most.
        </p>
    </div>
    """, unsafe_allow_html=True)

    _, center, _ = st.columns([1, 2, 1])

    with center:
        if st.button(
            "Start analyzing your resume",
            use_container_width=True,
            type="primary"
        ):
            st.session_state.current_view = "scorer"
            st.rerun()

    st.markdown(
        "<div class='section-kicker'>How it helps</div>",
        unsafe_allow_html=True,
    )
    st.markdown("## Resume feedback that is easy to act on")

    first, second, third = st.columns(3)

    with first:
        st.markdown("""
        <div class="feature-card">
            <h3>Comprehensive scoring</h3>
            <p>See how every part of your resume performs.</p>
            <ul>
                <li>Formatting</li>
                <li>Keywords &amp; skills</li>
                <li>Content quality</li>
                <li>ATS compatibility</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)

    with second:
        st.markdown("""
        <div class="feature-card">
            <h3>Skill validation</h3>
            <p>
                Check whether your claimed skills are actually
                demonstrated in your projects and experience.
            </p>
        </div>
        """, unsafe_allow_html=True)

    with third:
        st.markdown("""
        <div class="feature-card">
            <h3>Privacy first</h3>
            <p>
                Your analysis stays private, giving you room
                to improve confidently before you apply.
            </p>
        </div>
        """, unsafe_allow_html=True)

    st.markdown(
        "<br><div class='section-kicker'>Simple process</div>",
        unsafe_allow_html=True,
    )
    st.markdown("## From upload to next steps")

    one, two, three = st.columns(3)

    with one:
        st.markdown("""
        <div class="step-card">
            <div class="step-number">1</div>
            <h3>Upload</h3>
            <p>Add your PDF, DOC, or DOCX resume.</p>
        </div>
        """, unsafe_allow_html=True)

    with two:
        st.markdown("""
        <div class="step-card">
            <div class="step-number">2</div>
            <h3>Analyze</h3>
            <p>
                Review your resume across the dimensions
                that matter to ATS systems.
            </p>
        </div>
        """, unsafe_allow_html=True)

    with three:
        st.markdown("""
        <div class="step-card">
            <div class="step-number">3</div>
            <h3>Improve</h3>
            <p>
                Use clear recommendations to make your
                next revision count.
            </p>
        </div>
        """, unsafe_allow_html=True)