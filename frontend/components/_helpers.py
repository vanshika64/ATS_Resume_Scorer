from typing import Tuple


def get_score_color(score: float) -> Tuple[str, str]:
    """Return dark-theme foreground and background colours for a score."""
    if score >= 80:
        return "#9ed8af", "#213a2b"
    if score >= 60:
        return "#f0c070", "#43331e"
    return "#f09a90", "#442927"


def get_score_emoji(score: float) -> str:
    """Return a compact status marker for the overall score."""
    if score >= 90:
        return "\u2b50"
    if score >= 80:
        return "\u2705"
    if score >= 70:
        return "\U0001f44d"
    if score >= 60:
        return "\u26a0\ufe0f"
    return "\U0001f534"


def get_severity_style(severity: str) -> Tuple[str, str, str]:
    """Return a marker plus dark-theme foreground and background colours."""
    level = (severity or "").lower()
    if level in ("critical", "high"):
        return "\U0001f534", "#f09a90", "#442927"
    if level == "medium":
        return "\U0001f7e1", "#f0c070", "#43331e"
    return "\U0001f7e2", "#9ed8af", "#213a2b"
