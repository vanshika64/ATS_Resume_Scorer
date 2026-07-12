import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).parent.parent))

st.set_page_config(page_title="ATS Resume Vision", page_icon="🎯", layout="wide", initial_sidebar_state="collapsed")

for key, default in [
    ("access_token", None), ("refresh_token", None), ("user_id", None),
    ("user_email", None), ("auth_error", None), ("auth_info", None),
    ("current_view", "landing"), ("auth_mode", "signin"),
]:
    if key not in st.session_state:
        st.session_state[key] = default


def load_css() -> str:
    try:
        path = Path(__file__).parent / "assets" / "styles.css"
        return f"<style>{path.read_text(encoding='utf-8')}</style>"
    except FileNotFoundError:
        return ""


st.markdown(load_css(), unsafe_allow_html=True)

# Top-nav links set a query parameter. Consume it once so in-page buttons can
# still set a view through session state on later reruns.
requested_view = st.query_params.get("view")
if requested_view in {"landing", "scorer", "history", "resources", "auth"}:
    st.session_state.current_view = requested_view
    if requested_view == "auth":
        st.session_state.auth_mode = "signup" if st.query_params.get("mode") == "signup" else "signin"
    st.query_params.clear()
    st.rerun()

if not st.session_state.access_token and "code" in st.query_params:
    from frontend.services import supabase_client
    result = supabase_client.exchange_code_for_session(st.query_params["code"])
    st.query_params.clear()
    if "error" in result:
        st.session_state.auth_error = f"Google sign-in failed: {result['error']}"
        st.session_state.current_view = "auth"
    else:
        st.session_state.access_token = result["access_token"]
        st.session_state.refresh_token = result["refresh_token"]
        st.session_state.user_id = result["user_id"]
        st.session_state.user_email = result["email"]
    st.rerun()


def render_top_navigation() -> None:
    if st.session_state.access_token:
        account_links = (
            f"<span class='nav-user'>{st.session_state.user_email}</span>"
            "<a class='nav-action' href='?view=auth'>Account</a>"
        )
    else:
        account_links = (
            "<a class='nav-action' href='?view=auth'>Sign in</a>"
            "<a class='nav-action nav-action-primary' href='?view=auth&amp;mode=signup'>Sign up</a>"
        )
    st.markdown(
        f"""
        <nav class="top-navigation" aria-label="Main navigation">
          <a class="nav-brand" href="?view=landing">ATS Resume <span>Vision</span></a>
          <div class="nav-links">
            <a href="?view=landing">Home</a><a href="?view=scorer">ATS Scorer</a>
            <a href="?view=history">History</a><a href="?view=resources">Resources</a>
          </div>
          <div class="nav-account">{account_links}</div>
        </nav>
        """,
        unsafe_allow_html=True,
    )


def _render_auth_content() -> None:
    from frontend.services import supabase_client

    st.markdown("<div class='auth-page-heading'><div class='section-kicker'>Your account</div><h1>Welcome to ATS Resume Vision</h1><p>Sign in to analyze and save your resume feedback.</p></div>", unsafe_allow_html=True)
    if st.session_state.access_token:
        st.success(f"Signed in as {st.session_state.user_email}")
        if st.button("Sign out", type="primary"):
            supabase_client.sign_out()
            for key in ("access_token", "refresh_token", "user_id", "user_email"):
                st.session_state[key] = None
            st.session_state.current_view = "landing"
            st.rerun()
        return

    if st.session_state.auth_error:
        st.error(st.session_state.auth_error)
        st.session_state.auth_error = None
    if st.session_state.auth_info:
        st.info(st.session_state.auth_info)
        st.session_state.auth_info = None

    sign_in, sign_up = st.tabs(["Sign in", "Sign up"])
    with sign_in:
        with st.form("signin_form", clear_on_submit=False):
            email = st.text_input("Email", key="signin_email")
            password = st.text_input("Password", type="password", key="signin_pw")
            submitted = st.form_submit_button("Sign in", use_container_width=True)
        if submitted:
            result = supabase_client.sign_in_with_password(email, password)
            if "error" in result:
                st.session_state.auth_error = result["error"]
            else:
                st.session_state.access_token = result["access_token"]
                st.session_state.refresh_token = result["refresh_token"]
                st.session_state.user_id = result["user_id"]
                st.session_state.user_email = result["email"]
                st.session_state.current_view = "scorer"
            st.rerun()
    with sign_up:
        with st.form("signup_form", clear_on_submit=False):
            email_up = st.text_input("Email", key="signup_email")
            password_up = st.text_input("Password (min 6 chars)", type="password", key="signup_pw")
            submitted_up = st.form_submit_button("Create account", use_container_width=True)
        if submitted_up:
            result = supabase_client.sign_up_with_password(email_up, password_up)
            if "error" in result:
                st.session_state.auth_error = result["error"]
            elif result.get("pending_confirmation"):
                st.session_state.auth_info = f"Check your inbox — confirmation email sent to {result['email']}."
            else:
                st.session_state.access_token = result["access_token"]
                st.session_state.refresh_token = result["refresh_token"]
                st.session_state.user_id = result["user_id"]
                st.session_state.user_email = result["email"]
                st.session_state.current_view = "scorer"
            st.rerun()

    st.markdown("<div class='auth-divider'>or</div>", unsafe_allow_html=True)
    oauth = supabase_client.google_oauth_url()
    if "error" in oauth:
        st.caption(f"Google sign-in unavailable: {oauth['error']}")
    else:
        st.link_button("Continue with Google", url=oauth["url"], use_container_width=True)


def render_auth() -> None:
    """Keep account actions focused in a narrow, elevated main-page panel."""
    _, auth_column, _ = st.columns([1, 1.15, 1])
    with auth_column:
        with st.container(border=True):
            _render_auth_content()


render_top_navigation()

if st.session_state.current_view == "landing":
    from frontend.views import landing
    landing.render()
elif st.session_state.current_view == "scorer":
    from frontend.views import scorer
    scorer.render()
elif st.session_state.current_view == "history":
    from frontend.views import history
    history.render()
elif st.session_state.current_view == "resources":
    from frontend.views import resources
    resources.render()
elif st.session_state.current_view == "auth":
    render_auth()
