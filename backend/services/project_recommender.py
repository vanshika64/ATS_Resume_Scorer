"""Personalized, schema-checked project suggestions with a deterministic fallback."""

import json
import logging
import os
from typing import Any, Dict, List

logger = logging.getLogger("ats_resume_scorer")

PROJECT_SCHEMA = {
    "title": "",
    "description": "",
    "problem_solved": "",
    "skills_demonstrated": [],
    "technologies": [],
    "core_features": [],
    "implementation_stages": [],
    "difficulty": "Beginner|Intermediate|Advanced",
    "relevance": "",
    "skills_addressed": [],
    "resume_impact": "",
    "resume_bullet_structure": "",
}


def _fallback(role: str, gaps: List[str], demonstrated: List[str], projects: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    role_lower = (role or "software developer").lower()
    if any(key in role_lower for key in ("backend", "api", "server")):
        title, description, features, tools = "Reliable Service API", "Build a small API that solves a workflow relevant to the target role and makes reliability visible.", ["Design REST endpoints", "Add input validation and authentication", "Persist data", "Add automated tests and a CI workflow", "Document setup and API behavior"], ["Python", "FastAPI", "PostgreSQL", "Docker", "GitHub Actions"]
    elif any(key in role_lower for key in ("data", "analyst", "machine learning", "ml")):
        title, description, features, tools = "Reproducible Data Insights Pipeline", "Build a reproducible pipeline that turns a documented dataset into useful, reviewable insights.", ["Load and validate source data", "Transform data with documented assumptions", "Create a baseline analysis or model", "Expose results in a small dashboard or API", "Add tests and reproducible setup"], ["Python", "Pandas", "SQL", "scikit-learn", "Streamlit"]
    elif any(key in role_lower for key in ("frontend", "ui", "web")):
        title, description, features, tools = "Accessible Workflow Dashboard", "Build a responsive interface for a realistic workflow and connect it to a documented data source.", ["Create reusable interface components", "Support loading, empty, and error states", "Add accessible forms and navigation", "Connect to a small API", "Add component tests and deployment instructions"], ["TypeScript", "React", "CSS", "REST API", "Playwright"]
    else:
        title, description, features, tools = "Role-Focused Portfolio Application", "Build a compact application that applies the target role's core skills to a clear user problem.", ["Define a small user problem and requirements", "Build one end-to-end workflow", "Add validation and error handling", "Write tests and setup documentation", "Publish a demo if appropriate"], list(dict.fromkeys((demonstrated[:2] + gaps[:3] + ["Git", "Automated tests"])))
    covered = list(dict.fromkeys(gaps[:5] or ["project delivery", "testing", "documentation"]))
    return [{
        "title": title, "description": description,
        "problem_solved": "Provides a concrete, reviewable example of applying role-relevant skills.",
        "skills_demonstrated": covered, "technologies": list(dict.fromkeys(tools + covered))[:8],
        "core_features": features,
        "implementation_stages": ["Write a short scope and acceptance criteria", "Build the smallest end-to-end version", "Add tests and documentation", "Deploy or record a demo if practical"],
        "difficulty": "Intermediate" if len(covered) > 2 else "Beginner",
        "relevance": f"The idea is tailored to {role or 'the candidate profile'} and the resume evidence reviewed.",
        "skills_addressed": covered,
        "resume_impact": "Can provide verifiable evidence of implementation, testing, and technical decisions after completion.",
        "resume_bullet_structure": "[Action] [feature or system] using [technologies], addressing [problem]; include only outcomes you measured and can verify.",
        "personalization_basis": {"demonstrated_skills": demonstrated[:8], "existing_projects": [str(p.get("title", "")) for p in projects[:5] if isinstance(p, dict)], "skill_gaps": gaps[:8]},
    }]


def _valid(item: Any, gaps: List[str]) -> bool:
    if not isinstance(item, dict) or not isinstance(item.get("title"), str) or not item["title"].strip():
        return False
    for field in ("description", "problem_solved", "relevance", "resume_impact"):
        if not isinstance(item.get(field), str) or not item[field].strip():
            return False
    required_lists = ("skills_demonstrated", "technologies", "core_features", "implementation_stages", "skills_addressed")
    if any(not isinstance(item.get(key), list) or not item[key] or any(not isinstance(value, str) or not value.strip() for value in item[key]) for key in required_lists):
        return False
    difficulty = str(item.get("difficulty", "")).title()
    if difficulty not in {"Beginner", "Intermediate", "Advanced"}:
        return False
    addressed = {str(skill).casefold() for skill in item["skills_addressed"]}
    if gaps and not addressed.intersection(skill.casefold() for skill in gaps):
        return False
    item["difficulty"] = difficulty
    if not isinstance(item.get("resume_bullet_structure"), str) or not item["resume_bullet_structure"].strip():
        item["resume_bullet_structure"] = "[Action] [feature] using [technology]; add only outcomes you measured and can verify."
    guarantee_terms = ("guaranteed job", "guaranteed employment", "will get hired", "guaranteed shortlist")
    if any(term in str(item.get(key, "")).casefold() for key in ("description", "problem_solved", "relevance", "resume_impact") for term in guarantee_terms):
        return False
    return True


def recommend_projects(role: str, skills: List[str], projects: List[Dict[str, Any]], skill_details: List[Dict[str, Any]], jd_gaps: List[str]) -> Dict[str, Any]:
    demonstrated = [entry.get("skill", "") for entry in skill_details if entry.get("classification") == "Demonstrated"]
    evidence_gaps = [entry.get("skill", "") for entry in skill_details if entry.get("classification") in {"Weak Evidence", "Listed Only", "Not Found"}]
    gaps = list(dict.fromkeys([*jd_gaps, *evidence_gaps]))[:8]
    try:
        api_key = os.getenv("GROQ_API_KEY")
        if api_key and ((role or "").strip() or jd_gaps):
            from groq import Groq
            client = Groq(api_key=api_key)
            prompt = {
                "role": role or "General software role",
                "demonstrated_skills": demonstrated[:12],
                "resume_skills": (skills or [])[:20],
                "existing_projects": [{"title": p.get("title", ""), "technologies": p.get("technologies", [])} for p in (projects or [])[:8] if isinstance(p, dict)],
                "skill_gaps": gaps,
                "schema": {"recommendations": [PROJECT_SCHEMA]},
                "rules": ["Return valid JSON only.", "Return at most 3 practical projects.", "Address the supplied skill gaps and explain the connection.", "Do not invent candidate achievements or claim employment outcomes.", "Use a resume bullet template with placeholders for results not yet measured."],
            }
            response = client.chat.completions.create(
                model="openai/gpt-oss-120b", temperature=0.2, max_tokens=2500,
                messages=[{"role": "system", "content": "Create practical, personalized learning projects. Return a JSON object only."}, {"role": "user", "content": json.dumps(prompt)}],
            )
            raw = response.choices[0].message.content or "{}"
            result = json.loads(raw.strip().removeprefix("```json").removesuffix("```").strip())
            recs = result.get("recommendations", []) if isinstance(result, dict) else []
            valid = [item for item in recs[:3] if _valid(item, gaps)]
            if valid:
                for item in valid:
                    item["personalization_basis"] = {"demonstrated_skills": demonstrated[:8], "existing_projects": [str(p.get("title", "")) for p in projects[:5] if isinstance(p, dict)], "skill_gaps": gaps[:8]}
                return {"recommendations": valid, "source": "groq", "skill_gaps": gaps}
            logger.warning("Project recommendations failed schema or gap validation; using deterministic fallback")
    except Exception as exc:
        logger.warning("Project recommendation generation failed; using fallback: %s", exc)
    return {"recommendations": _fallback(role, gaps, demonstrated, projects or []), "source": "fallback", "skill_gaps": gaps}
