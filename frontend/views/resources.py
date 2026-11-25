import streamlit as st


def render() -> None:
    st.markdown("<div class='page-kicker'>Guides and references</div>", unsafe_allow_html=True)
    st.title("Resume resources")
    st.markdown("<p class='page-copy'>Practical formatting and writing guidance for resumes that are easier to scan and parse.</p>", unsafe_allow_html=True)

    st.markdown("## ATS-friendly fundamentals")
    left, right = st.columns(2)
    with left:
        with st.container(border=True):
            st.markdown("#### Clear structure")
            st.markdown("- Use standard section headings.\n- Keep important contact details in the main document body.\n- Prefer simple, consistent formatting.\n- Use a readable font and clear hierarchy.")
    with right:
        with st.container(border=True):
            st.markdown("#### Evidence and relevance")
            st.markdown("- Use job-description language where it accurately describes your experience.\n- Connect skills to specific project or work activities.\n- Describe methods and outcomes in concise bullets.\n- Include numeric results only when you can verify them.")

    st.markdown("## Common terms by field")
    technology, business, creative = st.tabs(["Technology", "Business", "Creative"])
    with technology:
        st.markdown("**Software development**\n\nProgramming languages, frameworks, databases, cloud platforms, version control, testing, API design, CI/CD and architecture patterns. Use the names and spelling that match your real experience.")
    with business:
        st.markdown("**Business and management**\n\nProject planning, stakeholder communication, budgeting, process improvement, reporting, operations and team leadership. Include these only when they reflect work you have done.")
    with creative:
        st.markdown("**Creative and design**\n\nUser research, prototyping, information architecture, accessibility, visual design, content strategy, brand systems and design tools. Describe your process and contribution.")

    st.markdown("## Keep the document easy to parse")
    st.markdown("Use a text-based PDF or DOCX, avoid decorative tables and text boxes for essential content, and review the extracted text after export. A clean format helps both automated parsers and people reading your resume.")
