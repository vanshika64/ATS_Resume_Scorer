"""Evidence-focused skill classification using parsed resume sections."""

import re
from typing import Any, Dict, List, Optional

import numpy as np


def _sentences(text: str) -> List[str]:
    return [part.strip(" •\t-\r\n") for part in re.split(r"(?<=[.!?])\s+|\n+", text or "") if len(part.strip()) > 4]


def _cosine(a: np.ndarray, b: np.ndarray) -> float:
    denominator = float(np.linalg.norm(a) * np.linalg.norm(b))
    return float(np.dot(a, b) / denominator) if denominator else 0.0


def classify_skills(
    skills: List[str], projects: List[Dict[str, Any]], experience: List[Dict[str, Any]],
    embedder: Any, job_skills: Optional[List[str]] = None,
) -> List[Dict[str, Any]]:
    """Classify listed skills and JD-only skills, preserving exact evidence snippets."""
    evidence: List[Dict[str, str]] = []
    for project in projects or []:
        if not isinstance(project, dict):
            continue
        label = str(project.get("title") or "Project")
        # Keep evidence verbatim from the resume description; parsed technology
        # lists and project titles are useful context but are not proof of use.
        body = str(project.get("description") or "")
        evidence.extend({"source_section": "Project", "source_name": label, "sentence": sentence} for sentence in _sentences(body))
    for role in experience or []:
        if not isinstance(role, dict):
            continue
        label = str(role.get("job_title") or role.get("company") or "Experience")
        evidence.extend({"source_section": "Experience", "source_name": label, "sentence": sentence} for sentence in _sentences(str(role.get("description") or "")))

    listed = list(dict.fromkeys(str(skill).strip() for skill in (skills or []) if str(skill).strip()))
    jd_only = [str(skill).strip() for skill in (job_skills or []) if str(skill).strip() and str(skill).strip().casefold() not in {s.casefold() for s in listed}]
    all_skills = list(dict.fromkeys(listed + jd_only))
    if not all_skills:
        return []

    # Encode in batches once. Fall back to literal matching if the embedder is unavailable.
    similarities: np.ndarray = np.zeros((len(all_skills), len(evidence)), dtype=float)
    if evidence and embedder is not None:
        try:
            vectors = np.asarray(embedder.encode(all_skills + [item["sentence"] for item in evidence], convert_to_tensor=False), dtype=float)
            skill_vectors = vectors[:len(all_skills)]
            sentence_vectors = vectors[len(all_skills):]
            for i, skill_vector in enumerate(skill_vectors):
                similarities[i] = [_cosine(skill_vector, sentence_vector) for sentence_vector in sentence_vectors]
        except Exception:
            pass

    results = []
    for index, skill in enumerate(all_skills):
        candidates = []
        for sentence_index, item in enumerate(evidence):
            sentence = item["sentence"]
            literal = bool(re.search(r"(?<!\w)" + re.escape(skill) + r"(?!\w)", sentence, re.IGNORECASE))
            similarity = max(0.0, min(1.0, float(similarities[index, sentence_index])))
            if literal or similarity >= 0.42:
                candidates.append((1.0 if literal else similarity, item, literal))
        candidates.sort(key=lambda candidate: candidate[0], reverse=True)
        best_score, best, literal = candidates[0] if candidates else (0.0, None, False)
        application_context = bool(best and re.search(
            r"\b(?:built|build|developed|designed|implemented|deployed|used|applied|created|integrated|automated|tested|maintained|configured|trained|analyzed|analysed|optimized|optimised|migrated|wrote|led|managed|authored|programmed)\b",
            best["sentence"], re.IGNORECASE,
        ))

        if best and best_score >= 0.60 and application_context:
            classification = "Demonstrated"
            explanation = f"The {best['source_section'].lower()} description connects {skill} to a concrete activity."
            recommendation = "Keep this example specific; clarify your contribution if it is not already clear."
        elif best:
            classification = "Weak Evidence"
            if literal and not application_context:
                explanation = f"{skill} is mentioned in the {best['source_section'].lower()} description, but the sentence does not clearly describe an action using it."
            else:
                explanation = f"The {best['source_section'].lower()} contains related language, but the practical use of {skill} is not explicit."
            recommendation = f"Clarify what you did with {skill}, where you used it, and the result if you can substantiate one."
        elif skill.casefold() in {entry.casefold() for entry in listed}:
            classification = "Listed Only"
            best = {"source_section": "Skills", "source_name": "Technical Skills", "sentence": ""}
            explanation = "The skill appears in the extracted skills list, but no supporting project or experience sentence was identified."
            recommendation = f"If accurate, add a project or experience bullet that shows how you applied {skill}."
        else:
            classification = "Not Found"
            best = None
            explanation = "This target requirement was not found in the extracted skills or supporting project and experience descriptions."
            recommendation = f"If you have this skill, add it to the resume and support it with a specific example; otherwise consider learning it."

        results.append({
            "skill": skill,
            "classification": classification,
            "source_section": best["source_section"] if best else "Not found",
            "source_name": best["source_name"] if best else "",
            "evidence": best["sentence"] if best else "",
            "explanation": explanation,
            "similarity": round(float(best_score), 3) if best else None,
            "recommendation": recommendation,
        })
    return results
