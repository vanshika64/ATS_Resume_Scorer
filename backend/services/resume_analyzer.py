import spacy
from sentence_transformers import SentenceTransformer
from typing import Dict, List, Optional
from backend.models.schemas import IssueDetail
from backend.services.groq_parser import parse_resume, parse_job_description
from backend.services.jd_matcher import compare_resume_with_jd
from backend.services.feedback_engine import analyze_issues, generate_issues_summary
from backend.services.ats_scorer import calculate_overall_score
from backend.services.skill_evidence import classify_skills
from backend.services.project_recommender import recommend_projects


def analyze_full_resume(
    resume_text: str,
    nlp: spacy.Language,
    embedder: SentenceTransformer,
    job_description: Optional[str] = None,
    target_role: Optional[str] = None,
) -> Dict:
    import logging
    logger = logging.getLogger('ats_resume_scorer')
    parsed_resume = parse_resume(resume_text)
    logger.info(f"Groq parsed summary: {parsed_resume.get('professional_summary', '')[:100]!r}")
    logger.info(f"Groq parsed skills count: {len(parsed_resume.get('skills', []))}")
    logger.info(f"Groq parsed experience count: {len(parsed_resume.get('experience', []))}")

    skills          = parsed_resume.get('skills', [])
    projects        = parsed_resume.get('projects', [])
    keywords        = parsed_resume.get('keywords', [])
    action_verbs    = parsed_resume.get('action_verbs', [])

    experience_months = sum(
        int(e.get('duration_months', 0))
        for e in parsed_resume.get('experience', [])
        if isinstance(e, dict)
    )

    contact_info = {
        'email':     parsed_resume.get('email'),
        'phone':     parsed_resume.get('phone'),
        'linkedin':  parsed_resume.get('linkedin'),
        'github':    parsed_resume.get('github'),
        'portfolio': None,
    }
    jd_comparison_result = None
    jd_keywords = None
    parsed_jd = {}
    if job_description and job_description.strip():
        parsed_jd = parse_job_description(job_description.strip())
        jd_keywords = list(set(
            parsed_jd.get('keywords', []) +
            parsed_jd.get('required_skills', []) +
            parsed_jd.get('preferred_skills', [])
        ))
        jd_comparison_result = compare_resume_with_jd(
            resume_text=resume_text,
            resume_keywords=keywords,
            resume_skills=skills,
            jd_text=job_description.strip(),
            jd_keywords=jd_keywords,
            embedder=embedder,
            nlp=nlp,
        )

    job_skills = list(dict.fromkeys(
        parsed_jd.get('required_skills', []) + parsed_jd.get('preferred_skills', [])
    )) if parsed_jd else []
    skill_evidence = classify_skills(
        skills=skills, projects=projects,
        experience=parsed_resume.get('experience', []),
        embedder=embedder, job_skills=job_skills,
    )
    demonstrated_entries = [item for item in skill_evidence if item['classification'] == 'Demonstrated']
    listed_entries = [item for item in skill_evidence if item['classification'] != 'Not Found']
    resume_skill_keys = {str(skill).strip().casefold() for skill in skills if str(skill).strip()}
    listed_count = sum(1 for item in listed_entries if item['skill'].casefold() in resume_skill_keys)
    demonstrated_count = sum(1 for item in demonstrated_entries if item['skill'].casefold() in resume_skill_keys)
    skill_validation_pct = demonstrated_count / listed_count if listed_count else 0.0
    skill_validation = {
        'validated_skills': [
            {'skill': item['skill'], 'projects': [item['source_name']] if item['source_section'] == 'Project' else [], 'similarity': item.get('similarity'), 'evidence': item.get('evidence', '')}
            for item in demonstrated_entries if item['skill'].casefold() in resume_skill_keys
        ],
        'unvalidated_skills': [item['skill'] for item in skill_evidence if item['skill'].casefold() in resume_skill_keys and item['classification'] != 'Demonstrated'],
        'validation_percentage': skill_validation_pct,
        'skill_project_mapping': {item['skill']: ([item['source_name']] if item.get('source_name') else []) for item in skill_evidence},
        'validation_score': skill_validation_pct * 15.0,
    }

    from backend.utils.file_utils import (
        get_default_grammar_results, get_default_location_results,
    )
    grammar_results  = get_default_grammar_results()
    location_results = get_default_location_results()

    scores = calculate_overall_score(
        text=resume_text,
        parsed_resume=parsed_resume,
        skills=skills,
        keywords=keywords,
        action_verbs=action_verbs,
        skill_validation_results=skill_validation,
        grammar_results=grammar_results,
        location_results=location_results,
        jd_keywords=jd_keywords,
        experience_months=experience_months,
    )
    detailed_feedback = analyze_issues(
        resume_text=resume_text,
        parsed_resume=parsed_resume,
        skills=skills,
        projects=projects,
        action_verbs=action_verbs,
        skill_validation=skill_validation,
        scores=scores,
        contact_info=contact_info,
    )

    issues_summary = generate_issues_summary(detailed_feedback)

    validated_raw   = skill_validation.get('validated_skills', [])
    unvalidated_raw = skill_validation.get('unvalidated_skills', [])
    total_skills    = len(resume_skill_keys)
    val_pct         = round((len(validated_raw) / total_skills * 100) if total_skills > 0 else 0, 1)

    skill_validation_details = {
        "validated": [
            {
                "skill":    item['skill'],
                "projects": item.get('projects', []),
                "similarity": item.get('similarity'),
            }
            for item in validated_raw
        ],
        "unvalidated":     unvalidated_raw,
        "total":           total_skills,
        "validated_count": len(validated_raw),
        "validation_pct":  val_pct,
        "skills": skill_evidence,
        "evidence_coverage_pct": round((demonstrated_count / listed_count * 100) if listed_count else 0.0, 1),
    }

    project_result = recommend_projects(
        role=(target_role or '').strip(), skills=skills, projects=projects,
        skill_details=skill_evidence,
        jd_gaps=(jd_comparison_result or {}).get('skills_gap', []),
    )

    return {
        "ATS_score":          scores['overall_score'],
        "ats_score":          scores['overall_score'],
        "component_scores": {
            "formatting":       scores['formatting_score'],
            "keywords":         scores['keywords_score'],
            "content":          scores['content_score'],
            "skill_validation": scores['skill_validation_score'],
            "ats_compatibility": scores['ats_compatibility_score'],
        },
        "issues_summary":    issues_summary,
        "detailed_feedback": detailed_feedback,
        "jd_match_analysis": jd_comparison_result,
        "jd_comparison":     jd_comparison_result,
        "skills":            skills,
        "matched_keywords":  (
            jd_comparison_result['matched_keywords']
            if jd_comparison_result else list(keywords[:20])
        ),
        "missing_keywords":  (
            jd_comparison_result['missing_keywords']
            if jd_comparison_result else []
        ),
        "strengths": _generate_strengths(parsed_resume, skills, projects, action_verbs, skill_validation, scores),
        "interpretation":    scores.get('overall_interpretation', ''),
        "skill_validation_details": skill_validation_details,
        "score_explanations": scores.get('score_explanations', []),
        "overall_score_explanation": scores.get('overall_score_explanation', {}),
        "project_recommendations": project_result.get('recommendations', []),
        "recommendations_source": project_result.get('source', 'fallback'),
        "target_role": (target_role or '').strip(),
        "projects": projects,
        "suggestions": list(dict.fromkeys([issue.how_to_fix for issue in detailed_feedback if issue.how_to_fix]))[:10],
        "critical_issues": [issue.issue_title for issue in detailed_feedback if str(issue.severity_level).lower() in {'high', 'critical'}],
        "experience_months": experience_months,
    }


def _generate_strengths(
    parsed_resume: Dict, skills: List, projects: List,
    action_verbs: List, skill_validation: Dict, scores: Dict,
) -> List[str]:
    """Generate a list of things the resume does well, based on actual structured data."""
    strengths = []

    if parsed_resume.get('experience'):
        strengths.append("Has a dedicated Experience section")
    if parsed_resume.get('projects') or len(projects) > 0:
        strengths.append("Includes a Projects section showcasing applied skills")
    if parsed_resume.get('education'):
        strengths.append("Education section is present")
    if parsed_resume.get('skills'):
        strengths.append("Clear Skills section with listed technologies")
    if parsed_resume.get('professional_summary', '').strip():
        strengths.append("Professional Summary provides a quick overview")

    if len(skills) >= 8:
        strengths.append(f"Strong skill set — {len(skills)} skills detected")
    if len(action_verbs) >= 5:
        strengths.append(f"Uses {len(action_verbs)} strong action verbs in bullet points")

    validated = skill_validation.get('validated_skills', [])
    if len(validated) >= 3:
        strengths.append(f"{len(validated)} skills are backed by project/experience evidence")

    if scores.get('formatting_score', 0) >= 16:
        strengths.append("Well-formatted and ATS-friendly structure")
    if scores.get('content_score', 0) >= 20:
        strengths.append("Content quality is high with measurable achievements")

    return strengths
