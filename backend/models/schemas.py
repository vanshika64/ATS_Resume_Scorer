from typing import Any, Dict, List, Optional
from pydantic import BaseModel

class ComponentScores(BaseModel):
    formatting: float
    keywords: float
    content: float
    skill_validation: float
    ats_compatibility: float

class JDComparison(BaseModel):
    match_percentage: float
    semantic_similarity: float
    matched_keywords: List[str]
    missing_keywords: List[str]
    skills_gap: List[str]

class SkillValidationDetails(BaseModel):
    validated: List[Dict[str, Any]] = []       # [{'skill': str, 'projects': [str]}]
    unvalidated: List[str] = []                # ['Flask', 'A/B Testing', ...]
    total: int = 0
    validated_count: int = 0
    validation_pct: float = 0.0
    skills: List[Dict[str, Any]] = []
    evidence_coverage_pct: float = 0.0

class ScoreExplanation(BaseModel):
    category: str
    obtained_score: float
    maximum_score: float
    reason: str = ""
    deductions: List[Dict[str, Any]] = []
    missing_elements: List[str] = []
    suggestions: List[str] = []
    evidence: List[str] = []

class ProjectRecommendationRequest(BaseModel):
    target_role: str = ""
    skills: List[str] = []
    projects: List[Dict[str, Any]] = []
    skill_details: List[Dict[str, Any]] = []
    jd_gaps: List[str] = []

class IssueDetail(BaseModel):
    issue_title: str
    severity_level: str
    ats_impact: str
    explanation: str
    where_it_appears: str
    how_to_fix: str
    action_items: List[str] = []
    example_improvement: str

class AnalysisResponse(BaseModel):
    ATS_score: float
    component_scores: ComponentScores
    issues_summary: List[str]
    detailed_feedback: List[IssueDetail]
    jd_match_analysis: Optional[JDComparison] = None
    skill_validation_details: Optional[SkillValidationDetails] = None

    ats_score: float
    keyword_match: float = 0.0
    missing_keywords: List[str] = []
    matched_keywords: List[str] = []
    suggestions: List[str] = []
    strengths: List[str] = []
    critical_issues: List[str] = []
    skills: List[str] = []
    jd_comparison: Optional[JDComparison] = None
    warnings: List[str] = []
    interpretation: str = ""
    score_explanations: List[ScoreExplanation] = []
    overall_score_explanation: Dict[str, Any] = {}
    project_recommendations: List[Dict[str, Any]] = []
    target_role: str = ""
    recommendations_source: str = ""
    projects: List[Dict[str, Any]] = []
