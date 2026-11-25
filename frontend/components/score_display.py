from html import escape
from typing import Any, Dict

import streamlit as st


COMPONENTS = [
    ("Formatting", "formatting", 20),
    ("Keywords and Skills", "keywords", 25),
    ("Content Quality", "content", 25),
    ("Skill Validation", "skill_validation", 15),
    ("ATS Compatibility", "ats_compatibility", 15),
]


def display_overall_score(analysis: Dict[str, Any]) -> None:
    score = min(100.0, max(0.0, float(analysis.get("ATS_score", analysis.get("ats_score", 0)) or 0)))
    interpretation = escape(str(analysis.get("interpretation", "") or ""))
    explanation = analysis.get("overall_score_explanation") or {}
    strongest = escape(str(explanation.get("strongest_category", "") or ""))
    weakest = escape(str(explanation.get("weakest_category", "") or ""))
    strongest_score = escape(str(explanation.get("strongest_score", "") or ""))
    weakest_score = escape(str(explanation.get("weakest_score", "") or ""))
    score_copy = f"<p>{interpretation}</p>" if interpretation else ""
    highlights = "".join(
        f"<span class='score-highlight'><strong>{label}:</strong> {category} {value}</span>"
        for label, category, value in (
            ("Strongest area", strongest, strongest_score),
            ("Most room to improve", weakest, weakest_score),
        ) if category
    )

    st.markdown("<div class='section-kicker'>Your results</div>", unsafe_allow_html=True)
    st.markdown(
        f"""
        <section class="score-hero" aria-label="Overall ATS score">
          <div class="score-ring" style="--score:{score:.1f}" role="img" aria-label="ATS score {score:.0f} out of 100">
            <div class="score-ring-inner"><span class="score-ring-value">{score:.0f}</span><span class="score-ring-denom">out of 100</span></div>
          </div>
          <div class="score-summary">
            <div class="page-kicker">Overall ATS score</div>
            <h2>Resume analysis</h2>
            {score_copy}
            <div class="score-highlights">{highlights}</div>
          </div>
        </section>
        """,
        unsafe_allow_html=True,
    )


def display_score_breakdown(analysis: Dict[str, Any]) -> None:
    component_scores = analysis.get("component_scores") or {}
    explanations = {item.get("category"): item for item in analysis.get("score_explanations", []) if isinstance(item, dict)}
    explanations.setdefault("Keywords and Skills", explanations.get("Keywords & Skills"))

    children = []
    for label, key, maximum in COMPONENTS:
        value = float(component_scores.get(key, 0) or 0)
        percentage = min(1.0, max(0.0, value / maximum))
        detail = explanations.get(label) or {}
        body = [
            f"<div class='score-breakdown-progress' role='img' aria-label='{percentage:.0%} of available points'>"
            f"<span style='width:{percentage * 100:.1f}%'></span></div>"
        ]
        if detail.get("reason"):
            body.append(f"<p>{escape(str(detail['reason']))}</p>")
        if detail.get("deductions"):
            body.append("<h4>What reduced the score</h4><ul>")
            for deduction in detail["deductions"]:
                points = deduction.get("points")
                points_copy = f" (−{points:g})" if isinstance(points, (int, float)) and points else ""
                item = escape(str(deduction.get("item", "Scoring signal")))
                evidence = escape(str(deduction.get("evidence", "")))
                body.append(f"<li><strong>{item}</strong>{points_copy}: {evidence}</li>")
            body.append("</ul>")
        if detail.get("missing_elements"):
            body.append("<h4>Missing elements</h4><ul>")
            body.extend(f"<li>{escape(str(item))}</li>" for item in detail["missing_elements"])
            body.append("</ul>")
        if detail.get("suggestions"):
            body.append("<h4>Ways to improve</h4><ul>")
            body.extend(f"<li>{escape(str(item))}</li>" for item in detail["suggestions"])
            body.append("</ul>")
        if detail.get("evidence"):
            body.append("<h4>Supporting signals</h4><ul>")
            body.extend(f"<li>{escape(str(item))}</li>" for item in detail["evidence"])
            body.append("</ul>")

        children.append(
            f"<details class='score-breakdown-child'>"
            f"<summary>{escape(label)} <span>{value:.0f} / {maximum} points</span></summary>"
            f"<div class='score-breakdown-child-body'>{''.join(body)}</div></details>"
        )

    overall = analysis.get("overall_score_explanation") or {}
    overall_content = []
    if overall.get("calculation"):
        overall_content.append(f"<p>{escape(str(overall['calculation']))}</p>")
    if overall.get("bonuses"):
        bonus_text = ", ".join(
            f"{escape(str(name).replace('_', ' '))} (+{points:g})"
            if isinstance(points, (int, float)) else f"{escape(str(name).replace('_', ' '))} ({escape(str(points))})"
            for name, points in overall["bonuses"].items()
        )
        overall_content.append(f"<p><strong>Bonuses:</strong> {bonus_text}</p>")
    if overall.get("penalties"):
        penalty_text = ", ".join(
            f"{escape(str(name).replace('_', ' '))} (−{points:g})"
            if isinstance(points, (int, float)) else f"{escape(str(name).replace('_', ' '))} ({escape(str(points))})"
            for name, points in overall["penalties"].items()
        )
        overall_content.append(f"<p><strong>Penalties:</strong> {penalty_text}</p>")
    intro = f"<div class='score-breakdown-overall'>{''.join(overall_content)}</div>" if overall_content else ""

    markup = (
        "<details class='score-breakdown-accordion'>"
        "<summary>Score Breakdown</summary>"
        f"<div class='score-breakdown-content'>{intro}{''.join(children)}</div>"
        "</details>"
    )
    st.markdown(markup, unsafe_allow_html=True)
