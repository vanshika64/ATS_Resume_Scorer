import html
import sys
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

sys.path.insert(0, str(Path(__file__).parent.parent))

st.set_page_config(page_title="ATS Resume Vision", page_icon="A", layout="wide", initial_sidebar_state="collapsed")

for key, default in [
    ("access_token", None), ("refresh_token", None), ("user_id", None),
    ("user_email", None), ("auth_error", None), ("auth_info", None),
    ("current_view", "landing"), ("auth_mode", "signin"),
]:
    if key not in st.session_state:
        st.session_state[key] = default


def load_css(theme: str) -> str:
    """Load shared CSS and resolve the persisted theme before rendering widgets."""
    path = Path(__file__).parent / "assets" / "styles.css"
    base = path.read_text(encoding="utf-8")
    if theme == "light":
        base += """
        <style>
        :root {
          color-scheme: light;
          --bg:#f3f5fa; --bg-raised:#f9faff; --surface:#ffffff; --surface-raised:#f4f5fb; --surface-soft:#e9ecf5;
          --text:#17213a; --text-secondary:#53617b; --text-muted:#73809a; --border:#dfe4ef; --border-strong:#c7d0e0;
          --accent:#6656d9; --accent-hover:#5141c7; --accent-soft:rgba(102,86,217,.11);
          --success:#188c69; --warning:#9c6815; --danger:#b33d51; --info:#2477ac;
          --shadow-sm:0 4px 14px rgba(31,42,69,.06); --shadow-md:0 18px 44px rgba(31,42,69,.09);
        }
        html, body, .stApp, [data-testid="stAppViewContainer"], [data-testid="stHeader"] { color-scheme:light; }
        .top-navigation { background:rgba(249,250,255,.94); }
        .hero-panel { background:linear-gradient(130deg,#fff,#f3f2ff 92%); }
        .score-hero { background:linear-gradient(120deg,#fff,#f6f5ff); }
        div[data-baseweb="popover"] *, [role="listbox"] *, [role="option"] { color:#17213a !important; }
        [data-testid="stFileUploader"] section { background:#fff !important; }
        </style>
        """
    return f"<style>{base}</style>"


theme = st.query_params.get("theme") or st.session_state.get("theme", "dark")
if theme not in {"dark", "light"}:
    theme = "dark"
st.session_state.theme = theme
st.markdown(load_css(theme), unsafe_allow_html=True)

# Keep the selected appearance in browser storage as well as the URL so it
# survives browser restarts and follows navigation between Streamlit views.
components.html(
    f"""<script>
    const selectedTheme = "{theme}";
    try {{
      localStorage.setItem("ats-resume-vision-theme", selectedTheme);
      window.parent.document.documentElement.dataset.theme = selectedTheme;
    }} catch (error) {{ /* URL and server state remain the persistent fallback. */ }}
    </script>""",
    height=0,
    scrolling=False,
)


def _consume_query(key: str) -> None:
    if key in st.query_params:
        del st.query_params[key]


action = st.query_params.get("action")
if action == "signout":
    from frontend.services import supabase_client
    supabase_client.sign_out()
    for key in ("access_token", "refresh_token", "user_id", "user_email"):
        st.session_state[key] = None
    st.session_state.current_view = "landing"
    _consume_query("action")
    _consume_query("view")
    st.rerun()

requested_view = st.query_params.get("view")
if requested_view in {"landing", "scorer", "history", "resources", "auth"}:
    st.session_state.current_view = requested_view
    mode = st.query_params.get("mode")
    if requested_view == "auth" and mode in {"signin", "signup"}:
        st.session_state.auth_mode = mode
        st.session_state.auth_mode_control = "Create account" if mode == "signup" else "Sign in"
    _consume_query("view")
    _consume_query("mode")
    st.rerun()

if not st.session_state.access_token and "code" in st.query_params:
    from frontend.services import supabase_client
    result = supabase_client.exchange_code_for_session(st.query_params["code"])
    _consume_query("code")
    _consume_query("state")
    if "error" in result:
        st.session_state.auth_error = f"Google sign-in failed: {result['error']}"
        st.session_state.current_view = "auth"
    else:
        st.session_state.access_token = result["access_token"]
        st.session_state.refresh_token = result["refresh_token"]
        st.session_state.user_id = result["user_id"]
        st.session_state.user_email = result["email"]
    st.rerun()


def _view_url(view: str, selected_theme: str, mode: str | None = None) -> str:
    url = f"?view={view}&theme={selected_theme}"
    return f"{url}&mode={mode}" if mode else url


def render_top_navigation() -> None:
    current = st.session_state.current_view
    selected_theme = st.session_state.theme
    next_theme = "light" if selected_theme == "dark" else "dark"
    account_is_active = current == "auth" and bool(st.session_state.access_token)
    links = [
        ("Home", "landing"), ("ATS Scorer", "scorer"),
        ("Analysis History", "history"), ("Resources", "resources"),
    ]
    link_html = "".join(
        f"<a class='{('is-active' if current == view else '')}' href='{_view_url(view, selected_theme)}' "
        f"{'aria-current=page' if current == view else ''}>{label}</a>"
        for label, view in links
    )
    if st.session_state.access_token:
        email = html.escape(st.session_state.user_email or "Account")
        account_html = (
            f"<span class='nav-user'>{email}</span>"
            f"<a class='nav-action {('is-active' if account_is_active else '')}' href='{_view_url('auth', selected_theme)}'>Account</a>"
            f"<a class='nav-action' href='?action=signout&view=landing&theme={selected_theme}'>Sign out</a>"
        )
    else:
        account_html = (
            f"<a class='nav-action' href='{_view_url('auth', selected_theme, 'signin')}'>Sign in</a>"
            f"<a class='nav-action nav-action-primary' href='{_view_url('auth', selected_theme, 'signup')}'>Create account</a>"
        )
    theme_icon = """<svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="4"/><path d="M12 2v2m0 16v2M4.93 4.93l1.41 1.41m11.32 11.32 1.41 1.41M2 12h2m16 0h2M4.93 19.07l1.41-1.41M17.66 6.34l1.41-1.41"/></svg>""" if next_theme == "light" else """<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M20.5 14.2A8.5 8.5 0 0 1 9.8 3.5 8.5 8.5 0 1 0 20.5 14.2Z"/></svg>"""
    theme_label = "Switch to light mode" if next_theme == "light" else "Switch to dark mode"
    st.markdown(
        f"""
        <nav class="top-navigation" aria-label="Main navigation">
          <a class="nav-brand" href="{_view_url('landing', selected_theme)}">
            <span class="nav-mark" aria-hidden="true"><svg viewBox="0 0 24 24"><path d="M5 18V6h3.2l3.8 5.2L15.8 6H19v12h-3V10.8l-3.9 5.1-4-5.1V18z"/></svg></span>
            ATS Resume Vision
          </a>
          <div class="nav-links">{link_html}</div>
          <div class="nav-account">
            <a class="nav-action nav-theme" href="?view={current}&theme={next_theme}" aria-label="{theme_label}" title="{theme_label}">{theme_icon}</a>
            {account_html}
          </div>
        </nav>
        """,
        unsafe_allow_html=True,
    )


def _render_product_intro() -> None:
    st.markdown(
        """
        <section class="auth-intro" aria-labelledby="auth-product-title">
          <div class="page-kicker">A clearer way to apply</div>
          <h1 id="auth-product-title">Build a Resume That Proves Your Potential.</h1>
          <p>Go beyond keyword matching. Understand your resume, validate your skills, identify gaps and discover projects that strengthen your career profile.</p>
          <div class="auth-benefits">
            <div class="auth-benefit"><span class="auth-benefit-icon" aria-hidden="true"><svg viewBox="0 0 24 24"><path d="M4 18V6m0 12h16M8 15v-4m4 4V7m4 8v-6"/></svg></span><span><strong>Transparent ATS Analysis</strong>Understand exactly why your resume receives its score.</span></div>
            <div class="auth-benefit"><span class="auth-benefit-icon" aria-hidden="true"><svg viewBox="0 0 24 24"><path d="M5 12.5 9.3 17 19 7"/><path d="M12 3 4 6v6c0 4.5 3.4 7.4 8 9 4.6-1.6 8-4.5 8-9V6z"/></svg></span><span><strong>Evidence-Based Skill Validation</strong>See whether your projects and experience support the skills you list.</span></div>
            <div class="auth-benefit"><span class="auth-benefit-icon" aria-hidden="true"><svg viewBox="0 0 24 24"><path d="M12 3v4m0 10v4M3 12h4m10 0h4M5.6 5.6l2.8 2.8m7.2 7.2 2.8 2.8m0-12.8-2.8 2.8m-7.2 7.2-2.8 2.8"/><circle cx="12" cy="12" r="3"/></svg></span><span><strong>Personalized Project Recommendations</strong>Find relevant projects based on your target role and skill gaps.</span></div>
          </div>
        </section>
        """,
        unsafe_allow_html=True,
    )


def _render_signed_in_account() -> None:
    st.markdown("<div class='page-kicker'>Profile</div><h1>Account settings</h1>", unsafe_allow_html=True)
    with st.container(border=True):
        st.markdown("#### Signed in")
        st.write(st.session_state.user_email or "Account connected")
        st.caption("Your account is managed through the connected authentication provider.")
        if st.button("Sign out", type="primary", key="account_signout"):
            from frontend.services import supabase_client
            supabase_client.sign_out()
            for key in ("access_token", "refresh_token", "user_id", "user_email"):
                st.session_state[key] = None
            st.session_state.current_view = "landing"
            st.rerun()


def _render_auth_forms() -> None:
    from frontend.services import supabase_client

    if st.session_state.access_token:
        _render_signed_in_account()
        return

    if st.session_state.auth_error:
        st.error(st.session_state.auth_error)
        st.session_state.auth_error = None
    if st.session_state.auth_info:
        st.info(st.session_state.auth_info)
        st.session_state.auth_info = None

    with st.container(border=True):
        mode_options = ["Sign in", "Create account"]
        default_index = 1 if st.session_state.auth_mode == "signup" else 0
        mode = st.radio("Account access", mode_options, index=default_index, horizontal=True, label_visibility="collapsed", key="auth_mode_control")
        st.session_state.auth_mode = "signup" if mode == "Create account" else "signin"

        if st.session_state.auth_mode == "signin":
            st.markdown("<h2 class='auth-card-heading'>Welcome back</h2><p class='auth-card-copy'>Sign in to continue to your resume workspace.</p>", unsafe_allow_html=True)
            with st.form("signin_form", clear_on_submit=False):
                email = st.text_input("Email", key="signin_email", placeholder="you@example.com")
                password = st.text_input("Password", type="password", key="signin_pw", placeholder="Enter your password")
                submitted = st.form_submit_button("Sign in", use_container_width=True, type="primary")
            if submitted:
                if not email.strip() or not password:
                    st.session_state.auth_error = "Enter your email and password to sign in."
                else:
                    result = supabase_client.sign_in_with_password(email.strip(), password)
                    if "error" in result:
                        st.session_state.auth_error = result["error"]
                    else:
                        st.session_state.access_token = result["access_token"]
                        st.session_state.refresh_token = result["refresh_token"]
                        st.session_state.user_id = result["user_id"]
                        st.session_state.user_email = result["email"]
                        st.session_state.current_view = "landing"
                st.rerun()
        else:
            st.markdown("<h2 class='auth-card-heading'>Create your account</h2><p class='auth-card-copy'>Set up your workspace to analyze and save resume feedback.</p>", unsafe_allow_html=True)
            with st.form("signup_form", clear_on_submit=False):
                email_up = st.text_input("Email", key="signup_email", placeholder="you@example.com")
                password_up = st.text_input("Password", type="password", key="signup_pw", placeholder="At least 6 characters")
                confirm_up = st.text_input("Confirm password", type="password", key="signup_confirm_pw", placeholder="Enter your password again")
                submitted_up = st.form_submit_button("Create account", use_container_width=True, type="primary")
            if submitted_up:
                if not email_up.strip():
                    st.session_state.auth_error = "Enter an email address to create an account."
                elif len(password_up) < 6:
                    st.session_state.auth_error = "Use a password with at least 6 characters."
                elif password_up != confirm_up:
                    st.session_state.auth_error = "The passwords do not match."
                else:
                    result = supabase_client.sign_up_with_password(email_up.strip(), password_up)
                    if "error" in result:
                        st.session_state.auth_error = result["error"]
                    elif result.get("pending_confirmation"):
                        st.session_state.auth_info = f"Check your inbox — confirmation email sent to {result['email']}."
                    else:
                        st.session_state.access_token = result["access_token"]
                        st.session_state.refresh_token = result["refresh_token"]
                        st.session_state.user_id = result["user_id"]
                        st.session_state.user_email = result["email"]
                        st.session_state.current_view = "landing"
                st.rerun()

        oauth = supabase_client.google_oauth_url()
        if "error" not in oauth:
            st.markdown("<div class='auth-divider'>or continue with</div>", unsafe_allow_html=True)
            st.link_button("Continue with Google", url=oauth["url"], use_container_width=True)


def render_auth() -> None:
    if st.session_state.access_token:
        _render_signed_in_account()
        return
    intro, auth = st.columns([1.1, .9], gap="large")
    with intro:
        _render_product_intro()
    with auth:
        _render_auth_forms()


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
