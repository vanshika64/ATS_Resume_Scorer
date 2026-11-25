from typing import Tuple


def get_score_color(score: float) -> Tuple[str, str]:
    """Return accessible foreground and background colors for a score."""
    if score >= 80:
        return "#4fc79b", "rgba(79,199,155,.12)"
    if score >= 60:
        return "#e5b765", "rgba(229,183,101,.12)"
    return "#e98289", "rgba(233,130,137,.12)"


def get_severity_class(severity: str) -> str:
    level = (severity or "").lower()
    if level in {"critical", "high"}:
        return "priority-high"
    if level in {"moderate", "medium"}:
        return "priority-medium"
    return "priority-low"
