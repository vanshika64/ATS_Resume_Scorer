import re
import spacy
import numpy as np
from sentence_transformers import SentenceTransformer
from typing import Dict, List, Optional, Tuple

from backend.utils.file_utils import log_warning
from backend.core.config import SENTENCE_TRANSFORMER_MODEL
from backend.utils.matching import fuzzy_match_keywords

ZIP_CODE_PATTERN = r'\b\d{5}(?:-\d{4})?\b'

STREET_ADDRESS_PATTERN = (
    r'\b\d+\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\s+'
    r'(?:Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd|Lane|Ln|Drive|Dr|Court|Ct|Circle|Cir|Way|Place|Pl)\b'
)

def _tier_score(n: float, tiers:list)-> float:
    for threshold, pts in tiers:
        if n>=threshold:
            return pts
    
    return 0.0

#Location/privacy detection
def detect_location_info(text: str, nlp: spacy.Language) -> Dict:
    locations = []

    #method01: spacy NER
    doc = nlp(text)
    for ent in doc.ents:
        if ent.label_ in ['GPE', 'LOC']:
            locations.append({'text': ent.text, 'type': ent.label_.lower(), 'start': ent.start_char})

    #moetod02: street address regx
    for match in re.finditer(STREET_ADDRESS_PATTERN, text, re.IGNORECASE):
        locations.append({'text': match.group(), 'type': 'address', 'start': match.start()})

    #method03: ZIP/PIN CODE REGEX PATTERN
    for match in re.finditer(ZIP_CODE_PATTERN, text):
        locations.append({'text': match.group(), 'type': 'zip', 'start': match.start()})

    has_address = any(loc['type'] == 'address' for loc in locations)
    has_zip     = any(loc['type'] == 'zip'     for loc in locations)

    if has_address and has_zip:
        privacy_risk, penalty = 'high', 5.0
    elif has_address or has_zip:
        privacy_risk, penalty = 'high', 4.0
    elif len(locations) > 3:
        privacy_risk, penalty = 'medium', 3.0
    elif locations:
        privacy_risk, penalty = 'low', 2.0
    else:
        privacy_risk, penalty = 'none', 0.0

    recommendations = []
    if not locations:
        recommendations.append(" No privacy concerns detected.")
    if has_address:
        recommendations.append(" Remove full street addresses — ATS systems don't need this and it's a privacy risk.")
    if has_zip:
        recommendations.append(" Remove zip codes — this level of location detail is unnecessary.")
    if privacy_risk in ('low', 'medium') and not has_address and not has_zip:
        recommendations.append(" Consider reducing location mentions. 'City, State' in the contact header is sufficient.")

    return {
        'location_found':     len(locations) > 0,
        'detected_locations': locations,
        'privacy_risk':       privacy_risk,
        'recommendations':    recommendations,
        'penalty_applied':    penalty,
    }

def _calculate_semantic_similarity(skill: str, text: str, embedder: SentenceTransformer) -> float:
    #similarity = (A · B) / (|A| × |B|)
    if not skill or not text:
        return 0.0
    try:
        skill_vec  = embedder.encode(skill, convert_to_tensor=False)
        text_vec   = embedder.encode(text,  convert_to_tensor=False)

        similarity = np.dot(skill_vec, text_vec) / (
            np.linalg.norm(skill_vec) * np.linalg.norm(text_vec)
        )

        return float(max(0.0, min(1.0, similarity)))
    except Exception as e:
        log_warning(f"Similarity error for '{skill}': {e}", context='ats_scorer')
        return 0.0

def _skill_matches(skill: str, text: str, embedder: SentenceTransformer, threshold: float) -> Tuple[bool, float]:

    #fast, o(n) directly check if skill is a substring of the text (case-insensitive)
    if skill.lower() in text.lower():
        return True, 1.0
    
    #slow, semantic similarity check using sentence embeddings
    sim = _calculate_semantic_similarity(skill, text, embedder)
    return sim >= threshold, sim

#Skill validation
def validate_skills_with_projects(
    skills: List[str],
    projects: List[Dict],
    experience_entries: List[Dict],
    embedder: SentenceTransformer,
    threshold: float = 0.6,
) -> Dict:
    
    if not skills:
        return {
            'validated_skills':      [],
            'unvalidated_skills':    [],
            'validation_percentage': 0.0,
            'skill_project_mapping': {},
            'validation_score':      0.0,
        }

    experience_text = ' '.join(
        f"{e.get('job_title', '')} {e.get('company', '')} {e.get('description', '')}"
        for e in experience_entries
        if isinstance(e, dict)
    ).strip()

    validated_skills      = []
    unvalidated_skills    = []
    skill_project_mapping = {}

    for skill in skills:
        matching_projects = []
        max_similarity    = 0.0

        for project in projects:
            project_text = f"{project.get('title', '')} {project.get('description', '')}"
            matched, sim = _skill_matches(skill, project_text, embedder, threshold)
            max_similarity = max(max_similarity, sim)

            if matched:
                matching_projects.append(project.get('title', 'Untitled Project'))

        if experience_text:
            matched, sim = _skill_matches(skill, experience_text, embedder, threshold)
            max_similarity = max(max_similarity, sim)
            if matched and 'Experience Section' not in matching_projects:
                matching_projects.append('Experience Section')

        if matching_projects:
            validated_skills.append({'skill': skill, 'projects': matching_projects, 'similarity': max_similarity})
            skill_project_mapping[skill] = matching_projects
        else:
            unvalidated_skills.append(skill)
            skill_project_mapping[skill] = []

    validation_percentage = len(validated_skills) / len(skills)
    validation_score      = validation_percentage * 15.0

    return {
        'validated_skills':      validated_skills,
        'unvalidated_skills':    unvalidated_skills,
        'validation_percentage': validation_percentage,
        'skill_project_mapping': skill_project_mapping,
        'validation_score':      validation_score,
    }

#01: formatting score
def _calc_formatting_score(parsed_resume: Dict, text: str) -> float:

    score = 0.0

    exp_entries  = [e for e in parsed_resume.get('experience', []) if isinstance(e, dict)]
    edu_entries  = [e for e in parsed_resume.get('education', [])  if isinstance(e, dict)]
    skills       = parsed_resume.get('skills', [])
    summary      = parsed_resume.get('professional_summary', '')
    proj_entries = [p for p in parsed_resume.get('projects', [])   if isinstance(p, dict)]

    if exp_entries and any(e.get('job_title') or e.get('description') for e in exp_entries):
        score += 3.0
    if edu_entries:
        score += 2.0
    if len(skills) >= 3:
        score += 2.0
    if len(summary) > 30:
        score += 1.5
    if proj_entries:
        score += 1.5

    bullet_count = sum(
        1 for line in text.split('\n')
        if re.match(r'^\s*[•\-\*\◦]', line) or re.match(r'^\s*\d+\.', line)
    )
    score += _tier_score(bullet_count, [(15,5.0),(10,4.0),(5,3.0),(3,2.0),(1,1.0)])

    filled = sum(1 for has_it in [
        bool(exp_entries), bool(edu_entries), bool(skills),
        bool(summary.strip()), bool(proj_entries),
    ] if has_it)
    score += _tier_score(filled, [(4,5.0),(3,4.0),(2,3.0),(1,2.0)])

    return min(20.0, max(0.0, score))

#02 keyword score
def _calc_keywords_score(
    resume_keywords: List[str],
    skills: List[str],
    jd_keywords: Optional[List[str]] = None,
) -> float:
    score = 0.0

    score += _tier_score(len(resume_keywords), [(20,10.0),(15,8.0),(10,6.0),(5,4.0),(3,2.0)])
    score += _tier_score(len(skills),          [(15,10.0),(10,8.0),(7,6.0),(5,4.0),(3,2.0)])

    if jd_keywords:
        all_resume_terms = list(set(resume_keywords + skills))
        fuzzy_result     = fuzzy_match_keywords(all_resume_terms, jd_keywords, threshold=80)
        match_pct        = len(fuzzy_result['matched']) / len(jd_keywords) if jd_keywords else 0
        score += _tier_score(match_pct, [(0.7,5.0),(0.5,4.0),(0.3,3.0),(0.2,2.0),(0.1,1.0)])
    
    elif len(resume_keywords) >= 10:
        score += 3.0

    return min(25.0, max(0.0, score))

#3. CONTENT QUALITY SCORE
def _calc_content_score(
    text: str,
    action_verbs: List[str],
    grammar_results: Dict,
) -> float:
    
    score = 0.0

    score += _tier_score(len(action_verbs), [(15,10.0),(10,8.0),(7,6.0),(5,4.0),(3,2.0)])

    number_patterns = [
        r'\d+%',
        r'\$\d+',
        r'\d+[kKmMbB]',
        r'\d+\s*(?:users|customers|clients|projects|hours|days|months|years)',
        r'(?:increased|decreased|improved|reduced|grew|saved)\s+(?:by\s+)?\d+',
    ]
    achievement_count = sum(len(re.findall(p, text, re.IGNORECASE)) for p in number_patterns)
    score += _tier_score(achievement_count, [(10,5.0),(7,4.0),(5,3.0),(3,2.0),(1,1.0)])

    grammar_penalty = grammar_results.get('penalty_applied', 0.0)
    score += max(0.0, 10.0 - grammar_penalty / 2.0)

    return min(25.0, max(0.0, score))

#4. SKILL VALIDATION SCORE
def _calc_skill_validation_score(validation_results: Dict) -> float:
    return min(15.0, max(0.0, validation_results.get('validation_score', 0.0)))

#5. ATS COMPATIBILITY SCORE
def _calc_ats_compatibility_score(
    text: str,
    location_results: Dict,
    parsed_resume: Dict,
) -> float:

    score = 15.0

    #dedeuction01
    score -= location_results.get('penalty_applied', 0.0)

    #deduction02
    special_chars = len(re.findall(r'[│┤├┼┴┬╔╗╚╝═║╠╣╦╩╬]', text))
    if special_chars > 20:    score -= 2.0
    elif special_chars > 10:  score -= 1.0

    exp_entries  = [e for e in parsed_resume.get('experience', []) if isinstance(e, dict)]
    edu_entries  = [e for e in parsed_resume.get('education', [])  if isinstance(e, dict)]
    skills_count = len(parsed_resume.get('skills', []))

    exp_desc_len = sum(len(e.get('description', '')) for e in exp_entries)
    edu_desc_len = sum(len((e.get('degree') or '') + (e.get('institution') or '')) for e in edu_entries)  # Handle None to prevent string concatenation errors

    #deduction03
    short_sections = sum([
        bool(exp_entries) and exp_desc_len < 20,
        bool(edu_entries) and edu_desc_len < 20,
        bool(parsed_resume.get('skills')) and skills_count < 2,
    ])
    if short_sections >= 2:    score -= 2.0
    elif short_sections >= 1:  score -= 1.0

    if exp_entries and skills_count > 5:
        score += 1.0

    return min(15.0, max(0.0, score))

#Score aggregation and final interpretation
def calculate_overall_score(
    text: str,
    parsed_resume: Dict,
    skills: List[str],
    keywords: List[str],
    action_verbs: List[str],
    skill_validation_results: Dict,
    grammar_results: Dict,
    location_results: Dict,
    jd_keywords: Optional[List[str]] = None,
    experience_months: int = 0,
) -> Dict:

    formatting_score        = _calc_formatting_score(parsed_resume, text)
    keywords_score          = _calc_keywords_score(keywords, skills, jd_keywords)
    content_score           = _calc_content_score(text, action_verbs, grammar_results)
    skill_validation_score  = _calc_skill_validation_score(skill_validation_results)
    ats_compatibility_score = _calc_ats_compatibility_score(text, location_results, parsed_resume)

    COMPONENT_MAX = {
        'formatting': 20.0, 'keywords': 25.0, 'content': 25.0,
        'skill_validation': 15.0, 'ats_compatibility': 15.0,
    }

    formatting_pct        = (formatting_score        / COMPONENT_MAX['formatting'])        * 100.0
    keywords_pct          = (keywords_score          / COMPONENT_MAX['keywords'])          * 100.0
    content_pct           = (content_score           / COMPONENT_MAX['content'])           * 100.0
    skill_validation_pct  = (skill_validation_score  / COMPONENT_MAX['skill_validation'])  * 100.0
    ats_compatibility_pct = (ats_compatibility_score / COMPONENT_MAX['ats_compatibility']) * 100.0

    skills_keywords_pct = (keywords_pct * 0.6) + (skill_validation_pct * 0.4)

    base_score = (
        skills_keywords_pct   * 0.40 +
        content_pct           * 0.30 +
        formatting_pct        * 0.15 +
        ats_compatibility_pct * 0.15
    )

    penalties = {}
    bonuses   = {}
    score     = base_score

    if grammar_results.get('penalty_applied', 0.0) > 0:
        penalties['grammar'] = grammar_results['penalty_applied']

    if location_results.get('penalty_applied', 0.0) > 0:
        penalties['location_privacy'] = location_results['penalty_applied']

    validation_pct = skill_validation_results.get('validation_percentage', 0.0)
    if validation_pct >= 0.9:
        bonuses['excellent_skill_validation'] = 2.0
        score += 2.0
    elif validation_pct >= 0.8:
        bonuses['good_skill_validation'] = 1.0
        score += 1.0

    if grammar_results.get('total_errors', 0) == 0:
        bonuses['perfect_grammar'] = 1.0
        score += 1.0

    if jd_keywords and len(jd_keywords) > 0:
        all_resume_terms = list(set((keywords or []) + (skills or [])))
        fuzzy_result     = fuzzy_match_keywords(all_resume_terms, jd_keywords, threshold=80)
        missing_pct      = len(fuzzy_result['missing']) / len(jd_keywords)

        if missing_pct > 0.7:
            penalties['missing_jd_keywords'] = 15.0
            score -= 15.0
        elif missing_pct > 0.5:
            penalties['missing_jd_keywords'] = 10.0
            score -= 10.0
        elif missing_pct > 0.3:
            penalties['missing_jd_keywords'] = 5.0
            score -= 5.0

    overall_score = min(100.0, max(0.0, score))
    interpretation = _generate_score_interpretation(overall_score)

    score_explanations = build_score_explanations(
        text=text, parsed_resume=parsed_resume, keywords=keywords, skills=skills,
        action_verbs=action_verbs, validation_results=skill_validation_results,
        grammar_results=grammar_results, location_results=location_results,
        jd_keywords=jd_keywords,
        scores={
            'formatting': formatting_score, 'keywords': keywords_score,
            'content': content_score, 'skill_validation': skill_validation_score,
            'ats_compatibility': ats_compatibility_score,
        },
    )
    sorted_components = sorted(
        score_explanations, key=lambda item: item['obtained_score'] / item['maximum_score']
    )
    strongest = sorted_components[-1] if sorted_components else None
    weakest = sorted_components[0] if sorted_components else None

    return {
        'overall_score':           round(overall_score, 1),
        'formatting_score':        round(formatting_score, 1),
        'keywords_score':          round(keywords_score, 1),
        'content_score':           round(content_score, 1),
        'skill_validation_score':  round(skill_validation_score, 1),
        'ats_compatibility_score': round(ats_compatibility_score, 1),
        'overall_interpretation':  interpretation,
        'penalties':               penalties,
        'bonuses':                 bonuses,
        'score_explanations':      score_explanations,
        'overall_score_explanation': {
            'summary': interpretation,
            'calculation': 'The original model combines normalized Keywords and Skills Validation (40%), Content Quality (30%), Formatting (15%), and ATS Compatibility (15%), then applies its existing grammar, privacy, skill-validation, and job-description adjustments. The displayed component maximums remain 20/25/25/15/15.',
            'strongest_category': strongest['category'] if strongest else '',
            'weakest_category': weakest['category'] if weakest else '',
            'strongest_score': f"{strongest['obtained_score']}/{strongest['maximum_score']}" if strongest else '',
            'weakest_score': f"{weakest['obtained_score']}/{weakest['maximum_score']}" if weakest else '',
            'bonuses': bonuses,
            'penalties': penalties,
        },
    }


def build_score_explanations(
    text: str, parsed_resume: Dict, keywords: List[str], skills: List[str],
    action_verbs: List[str], validation_results: Dict, grammar_results: Dict,
    location_results: Dict, jd_keywords: Optional[List[str]], scores: Dict,
) -> List[Dict]:
    """Explain component scores using the same measurable signals as the scorer."""
    def tier(value, tiers):
        return _tier_score(value, tiers)

    resume_keywords = keywords or []
    exp = [entry for entry in parsed_resume.get('experience', []) if isinstance(entry, dict)]
    edu = [entry for entry in parsed_resume.get('education', []) if isinstance(entry, dict)]
    projects = [entry for entry in parsed_resume.get('projects', []) if isinstance(entry, dict)]
    summary = parsed_resume.get('professional_summary') or ''
    bullet_count = sum(1 for line in text.split('\n') if re.match(r'^\s*[•\-*◦]', line) or re.match(r'^\s*\d+\.', line))
    filled = sum(bool(value) for value in (exp, edu, skills, summary.strip(), projects))
    achievement_patterns = [r'\d+%', r'\$\d+', r'\d+[kKmMbB]', r'\d+\s*(?:users|customers|clients|projects|hours|days|months|years)', r'(?:increased|decreased|improved|reduced|grew|saved)\s+(?:by\s+)?\d+']
    achievement_count = sum(len(re.findall(pattern, text, re.IGNORECASE)) for pattern in achievement_patterns)
    grammar_penalty = float(grammar_results.get('penalty_applied', 0.0) or 0.0)
    validated = validation_results.get('validated_skills', []) or []
    unvalidated = validation_results.get('unvalidated_skills', []) or []
    keyword_matches = fuzzy_match_keywords(list(set(resume_keywords + (skills or []))), jd_keywords or [], threshold=80) if jd_keywords else {'matched': [], 'missing': []}

    format_parts = [
        ('experience details', 3.0 if exp and any(item.get('job_title') or item.get('description') for item in exp) else 0.0, 'Add a clear role title or description to experience entries.'),
        ('education section', 2.0 if edu else 0.0, 'Add an Education section if applicable.'),
        ('skills list', 2.0 if len(skills or []) >= 3 else 0.0, 'List at least three relevant skills you can substantiate.'),
        ('professional summary', 1.5 if len(summary) > 30 else 0.0, 'Add a concise summary of more than 30 characters if useful for your profile.'),
        ('project section', 1.5 if projects else 0.0, 'Add projects if you have relevant work to show.'),
    ]
    format_bullets = tier(bullet_count, [(15,5.0),(10,4.0),(5,3.0),(3,2.0),(1,1.0)])
    format_structure = tier(filled, [(4,5.0),(3,4.0),(2,3.0),(1,2.0)])
    format_score = sum(part[1] for part in format_parts) + format_bullets + format_structure
    format_missing = [part[2] for part in format_parts if part[1] == 0.0]
    if format_bullets < 5:
        format_missing.append(f'Only {bullet_count} bullet-style lines were detected; the top tier requires 15.')
    if format_structure < 5:
        format_missing.append(f'{filled} of 5 parsed resume sections contain content; the top tier requires 4.')

    keyword_count_points = tier(len(resume_keywords), [(20,10.0),(15,8.0),(10,6.0),(5,4.0),(3,2.0)])
    skill_count_points = tier(len(skills or []), [(15,10.0),(10,8.0),(7,6.0),(5,4.0),(3,2.0)])
    if jd_keywords:
        match_ratio = len(keyword_matches['matched']) / len(jd_keywords)
        jd_points = tier(match_ratio, [(0.7,5.0),(0.5,4.0),(0.3,3.0),(0.2,2.0),(0.1,1.0)])
    else:
        match_ratio = None
        jd_points = 3.0 if len(resume_keywords) >= 10 else 0.0
    keyword_missing = []
    if keyword_count_points < 10:
        keyword_missing.append(f'{len(resume_keywords)} resume keywords detected; the top tier requires 20.')
    if skill_count_points < 10:
        keyword_missing.append(f'{len(skills or [])} skills detected; the top tier requires 15.')
    if jd_keywords and jd_points < 5:
        keyword_missing.append(f'{len(keyword_matches["missing"])} of {len(jd_keywords)} job-description keywords were not matched.')
    if not jd_keywords:
        keyword_missing.append('No job description was supplied; this path uses the existing general keyword rule instead of JD-specific coverage.')

    verb_points = tier(len(action_verbs or []), [(15,10.0),(10,8.0),(7,6.0),(5,4.0),(3,2.0)])
    achievement_points = tier(achievement_count, [(10,5.0),(7,4.0),(5,3.0),(3,2.0),(1,1.0)])
    grammar_points = max(0.0, 10.0 - grammar_penalty / 2.0)
    content_missing = []
    if verb_points < 10:
        content_missing.append(f'{len(action_verbs or [])} action verbs detected; the top tier requires 15.')
    if achievement_points < 5:
        content_missing.append(f'{achievement_count} quantified achievement patterns detected; the top tier requires 10.')
    if grammar_points < 10:
        content_missing.append(f'Grammar checks applied a {grammar_penalty:g}-point penalty.')

    unvalidated_names = [entry if isinstance(entry, str) else entry.get('skill', '') for entry in unvalidated]
    skill_missing = [f'{len(unvalidated_names)} of {len(validated) + len(unvalidated_names)} listed skills lacked evidence under the scorer matching rule.'] if unvalidated_names else []
    location_penalty = float(location_results.get('penalty_applied', 0.0) or 0.0)
    special_count = len(re.findall(r'[│┤├┼┴┬╔╗╚╝═║╠╣╦╩╬]', text))
    exp_desc_len = sum(len(item.get('description', '') or '') for item in exp)
    edu_desc_len = sum(len((item.get('degree') or '') + (item.get('institution') or '')) for item in edu)
    short_sections = sum([bool(exp) and exp_desc_len < 20, bool(edu) and edu_desc_len < 20, bool(skills) and len(skills) < 2])
    ats_deductions = []
    if location_penalty:
        ats_deductions.append({'item': 'Location privacy', 'points': location_penalty, 'evidence': 'Address/location patterns detected in the resume.'})
    if special_count > 10:
        points = 2.0 if special_count > 20 else 1.0
        ats_deductions.append({'item': 'Decorative line characters', 'points': points, 'evidence': f'{special_count} matching special characters detected.'})
    if short_sections:
        points = 2.0 if short_sections >= 2 else 1.0
        ats_deductions.append({'item': 'Very short parsed sections', 'points': points, 'evidence': f'{short_sections} section length checks were below the scorer threshold.'})

    data = [
        ('Formatting', 'formatting', 20.0, scores['formatting'], format_missing, [part[0] for part in format_parts if part[1] > 0] + ([f'{bullet_count} bullet-style lines'] if bullet_count else [])),
        ('Keywords and Skills', 'keywords', 25.0, scores['keywords'], keyword_missing, [f'{len(resume_keywords)} resume keywords', f'{len(skills or [])} extracted skills'] + ([f'{len(keyword_matches["matched"])} of {len(jd_keywords)} JD keywords matched'] if jd_keywords else [])),
        ('Content Quality', 'content', 25.0, scores['content'], content_missing, [f'{len(action_verbs or [])} action verbs', f'{achievement_count} quantified achievement patterns']),
        ('Skill Validation', 'skill_validation', 15.0, scores['skill_validation'], skill_missing, [f'{len(validated)} skills matched project or experience text', f'{len(unvalidated_names)} listed skills had no match']),
        ('ATS Compatibility', 'ats_compatibility', 15.0, scores['ats_compatibility'], [], [f'{special_count} decorative line characters', f'{short_sections} short-section checks', f'{location_penalty:g} location privacy penalty']),
    ]
    evidence_by_key = {
        'formatting': [line.strip() for line in text.splitlines() if re.match(r'^\s*[•\-*◦]|^\s*\d+\.', line)][:3],
        'keywords': [line.strip() for line in text.splitlines() if any(term and term.casefold() in line.casefold() for term in list(skills or [])[:12])][:5],
        'content': [line.strip() for line in text.splitlines() if re.match(r'^\s*[•\-*◦]|^\s*\d+\.', line) and any(re.search(pattern, line, re.IGNORECASE) for pattern in achievement_patterns)][:5],
        'skill_validation': [str(entry.get('evidence')) for entry in validated if isinstance(entry, dict) and entry.get('evidence')],
        'ats_compatibility': [str(item.get('text')) for item in location_results.get('detected_locations', [])[:5] if isinstance(item, dict) and item.get('text')],
    }
    result = []
    for label, key, maximum, score, missing, evidence in data:
        fraction = score / maximum if maximum else 0
        reason = f'{label} earned {score:g}/{maximum:g} based on the measured resume signals listed below.'
        if key == 'ats_compatibility' and ats_deductions:
            deductions = ats_deductions
        elif key == 'skill_validation':
            deductions = [{'item': 'Skills without matching project or experience evidence', 'points': round(maximum - score, 2), 'evidence': ', '.join(unvalidated_names[:8]) or 'No matching evidence found.'}] if score < maximum else []
        elif key == 'formatting':
            deductions = [
                {'item': item[0], 'points': round((3.0,2.0,2.0,1.5,1.5)[index] - item[1], 1), 'evidence': item[2]}
                for index, item in enumerate(format_parts) if item[1] < (3.0,2.0,2.0,1.5,1.5)[index]
            ]
            max_bullet_points = 5.0
            deductions += ([{'item': 'Bullet-line count', 'points': round(max_bullet_points-format_bullets, 1), 'evidence': f'{bullet_count} bullet-style lines detected.'}] if format_bullets < max_bullet_points else [])
            deductions += ([{'item': 'Parsed section coverage', 'points': round(5.0-format_structure, 1), 'evidence': f'{filled} of 5 section types were populated.'}] if format_structure < 5 else [])
        elif key == 'keywords':
            deductions = ([{'item': 'Resume keyword count', 'points': round(10.0-keyword_count_points, 1), 'evidence': f'{len(resume_keywords)} keywords detected.'}] if keyword_count_points < 10 else [])
            deductions += ([{'item': 'Extracted skill count', 'points': round(10.0-skill_count_points, 1), 'evidence': f'{len(skills or [])} skills detected.'}] if skill_count_points < 10 else [])
            if jd_keywords:
                deductions += ([{'item': 'Job keyword coverage', 'points': round(5.0-jd_points, 1), 'evidence': f'{len(keyword_matches["matched"])} of {len(jd_keywords)} requirements matched.'}] if jd_points < 5 else [])
        elif key == 'content':
            deductions = ([{'item': 'Action-verb count', 'points': round(10.0-verb_points, 1), 'evidence': f'{len(action_verbs or [])} action verbs detected.'}] if verb_points < 10 else [])
            deductions += ([{'item': 'Quantified-achievement patterns', 'points': round(5.0-achievement_points, 1), 'evidence': f'{achievement_count} patterns detected.'}] if achievement_points < 5 else [])
            deductions += ([{'item': 'Grammar penalty', 'points': round(10.0-grammar_points, 1), 'evidence': f'{grammar_penalty:g} penalty points from grammar checks.'}] if grammar_points < 10 else [])
        else:
            deductions = []
        suggestions = missing[:]
        if key == 'keywords' and jd_keywords:
            suggestions += [f'Address the job requirement “{term}” only if it reflects your real skills or experience.' for term in keyword_matches['missing'][:5]]
        result.append({'category': label, 'obtained_score': round(float(score), 1), 'maximum_score': maximum, 'reason': reason, 'deductions': deductions, 'missing_elements': missing, 'suggestions': suggestions[:8], 'evidence': evidence_by_key.get(key) or evidence})
    return result

#Overall score calculation and interpretation
def generate_strengths(
    score_results: Dict,
    skill_validation_results: Dict,
    grammar_results: Dict,
) -> List[str]:

    strengths = []

    if score_results['formatting_score']       >= 16:
        strengths.append(' Well-structured with clear sections and bullet points')
    if score_results['keywords_score']          >= 20:
        strengths.append(' Strong keyword optimization and skills presence')
    if score_results['content_score']           >= 20:
        strengths.append(' Excellent use of action verbs and quantifiable achievements')
    if score_results['skill_validation_score']  >= 12:
        pct = skill_validation_results.get('validation_percentage', 0) * 100
        strengths.append(f' {pct:.0f}% of skills are validated by projects')
    if score_results['ats_compatibility_score'] >= 13:
        strengths.append(' Excellent ATS compatibility with clean formatting')
    if grammar_results.get('total_errors', 0)   == 0:
        strengths.append(' Error-free grammar and spelling')

    if not strengths:
        strengths.append('Your resume has potential - focus on the recommendations below')
    return strengths


#Critical issues that could cause ATS rejection
def generate_critical_issues(
    score_results: Dict,
    grammar_results: Dict,
    location_results: Dict,
) -> List[str]:
    issues = []

    critical_errors = len(grammar_results.get('critical_errors', []))
    if critical_errors > 0:
        issues.append(f' {critical_errors} critical grammar/spelling error(s) detected')
    if location_results.get('privacy_risk') == 'high':
        issues.append('High privacy risk: Remove detailed location information')
    if score_results['formatting_score']       < 10:
        issues.append(' Poor formatting: Add clear sections and bullet points')
    if score_results['keywords_score']         < 12:
        issues.append(' Insufficient keywords and skills')
    if score_results['skill_validation_score'] < 7:
        issues.append(' Most skills lack supporting evidence in projects')

    return issues


#Actionable improvements to enhance ATS performance
def generate_improvements(
    score_results: Dict,
    skill_validation_results: Dict,
) -> List[str]:
    improvements = []

    if 12 <= score_results['formatting_score']       < 16:
        improvements.append('Add more bullet points and improve section organization')
    if 14 <= score_results['keywords_score']          < 20:
        improvements.append('Include more relevant keywords and technical skills')
    if 14 <= score_results['content_score']           < 20:
        improvements.append('Add more quantifiable achievements and action verbs')
    if 7  <= score_results['skill_validation_score']  < 12:
        unvalidated_count = len(skill_validation_results.get('unvalidated_skills', []))
        improvements.append(f'Validate {unvalidated_count} skill(s) by adding relevant project details')
    if 9  <= score_results['ats_compatibility_score'] < 13:
        improvements.append('Simplify formatting for better ATS compatibility')

    return improvements

#Interpretation of overall score
def _generate_score_interpretation(overall_score: float) -> str:
    if overall_score >= 90:    return 'Excellent! Your resume is highly optimized for ATS systems.'
    elif overall_score >= 80:  return 'Great! Your resume should perform well with most ATS systems.'
    elif overall_score >= 70:  return 'Good! Your resume is ATS-friendly with room for minor improvements.'
    elif overall_score >= 60:  return 'Fair. Your resume needs some improvements to be fully ATS-compatible.'
    elif overall_score >= 50:  return 'Below Average. Significant improvements needed for ATS compatibility.'
    else:                      return 'Poor. Your resume requires major revisions to pass ATS screening.'
