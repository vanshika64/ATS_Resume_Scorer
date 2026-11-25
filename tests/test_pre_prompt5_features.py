import unittest
from io import BytesIO
from unittest.mock import patch

import numpy as np

from backend.services.ats_scorer import calculate_overall_score
from backend.services.project_recommender import recommend_projects
from backend.services.report_generator import generate_html_reports
from backend.services.pdf_export import generate_combined_pdf
from backend.api.routes import generate_pdf as generate_pdf_endpoint
from PyPDF2 import PdfReader
from backend.services.skill_evidence import classify_skills
from backend.services.resume_analyzer import analyze_full_resume
from backend.models.schemas import AnalysisResponse, ComponentScores, JDComparison, SkillValidationDetails


class FakeEmbedder:
    def encode(self, texts, convert_to_tensor=False):
        if isinstance(texts, str):
            texts = [texts]
        vectors = []
        for text in texts:
            normalized = text.casefold()
            vectors.append([
                float("python" in normalized or "fastapi" in normalized),
                float("database" in normalized or "postgres" in normalized or "sql" in normalized or "backend engineering" in normalized or "web services" in normalized),
                float("react" in normalized or "interface" in normalized),
                0.0,
            ])
        return np.asarray(vectors)


class SkillEvidenceTests(unittest.TestCase):
    def test_listed_skill_with_exact_project_evidence_is_demonstrated(self):
        result = classify_skills(
            ["Python"],
            [{"title": "Resume API", "description": "Built a resume service using Python and FastAPI."}],
            [], FakeEmbedder(),
        )
        self.assertEqual(result[0]["classification"], "Demonstrated")
        self.assertEqual(result[0]["source_name"], "Resume API")
        self.assertEqual(result[0]["evidence"], "Built a resume service using Python and FastAPI.")

    def test_project_technology_stack_and_description_together_support_skill(self):
        result = classify_skills(
            ["Python"],
            [{"title": "ATS Analyzer", "technologies": ["Python", "FastAPI"], "description": "Developed a FastAPI backend for resume parsing and job-description matching."}],
            [], FakeEmbedder(),
        )
        self.assertEqual(result[0]["classification"], "Demonstrated")
        self.assertIn("technology stack", result[0]["explanation"])
        self.assertEqual(result[0]["evidence"], "Developed a FastAPI backend for resume parsing and job-description matching.")

    def test_listed_without_support_is_listed_only_and_job_gap_is_not_found(self):
        result = classify_skills(["Docker"], [], [], FakeEmbedder(), ["Kubernetes"])
        by_skill = {item["skill"]: item for item in result}
        self.assertEqual(by_skill["Docker"]["classification"], "Listed Only")
        self.assertEqual(by_skill["Kubernetes"]["classification"], "Not Found")

    def test_experience_evidence_is_distinguished_from_project_evidence(self):
        result = classify_skills(
            ["Python"], [],
            [{"job_title": "Developer", "description": "Automated a workflow using Python for internal reporting."}],
            FakeEmbedder(),
        )
        self.assertEqual(result[0]["classification"], "Demonstrated")
        self.assertEqual(result[0]["source_section"], "Experience")

    def test_semantic_paraphrase_can_be_weak_evidence_and_irrelevant_text_does_not_match(self):
        class ParaphraseEmbedder(FakeEmbedder):
            def encode(self, texts, convert_to_tensor=False):
                if isinstance(texts, str):
                    texts = [texts]
                return np.asarray([[0, 1, 0, 0] if "backend engineering" in text.casefold() or "web services" in text.casefold() else [0, 0, 0, 0] for text in texts])

        paraphrase = classify_skills(["Backend Engineering"], [{"title": "API", "description": "Built web services for a campus booking workflow."}], [], ParaphraseEmbedder())
        self.assertEqual(paraphrase[0]["classification"], "Demonstrated")
        unrelated = classify_skills(["Go"], [{"title": "Notes", "description": "Reviewed ongoing project notes."}], [], FakeEmbedder())
        self.assertEqual(unrelated[0]["classification"], "Listed Only")

    def test_keyword_stuffing_without_an_action_is_not_demonstrated(self):
        result = classify_skills(["Python"], [{"title": "Project", "description": "Python Python Python Python."}], [], FakeEmbedder())
        self.assertEqual(result[0]["classification"], "Weak Evidence")


class ScoringExplanationTests(unittest.TestCase):
    def test_component_limits_and_explanations_match_calculated_scores(self):
        scores = calculate_overall_score(
            text="SKILLS\nPython\nPROJECTS\n• Built a data tool using Python for reporting.",
            parsed_resume={"skills": ["Python"], "projects": [{"title": "Data Tool"}], "education": [], "experience": [], "professional_summary": ""},
            skills=["Python"], keywords=["Python", "data tool"], action_verbs=["Built"],
            skill_validation_results={"validated_skills": [], "unvalidated_skills": ["Python"], "validation_percentage": 0, "validation_score": 0},
            grammar_results={"penalty_applied": 0, "total_errors": 0},
            location_results={"penalty_applied": 0, "detected_locations": []},
        )
        maxima = {"formatting_score": 20, "keywords_score": 25, "content_score": 25, "skill_validation_score": 15, "ats_compatibility_score": 15}
        for key, maximum in maxima.items():
            self.assertGreaterEqual(scores[key], 0)
            self.assertLessEqual(scores[key], maximum)
        self.assertGreaterEqual(scores["overall_score"], 0)
        self.assertLessEqual(scores["overall_score"], 100)
        explanation_scores = {item["category"]: item["obtained_score"] for item in scores["score_explanations"]}
        self.assertEqual(explanation_scores["Content Quality"], scores["content_score"])
        self.assertEqual(explanation_scores["Skill Validation"], scores["skill_validation_score"])
        self.assertTrue(scores["overall_score_explanation"]["calculation"])


class AnalyzerIntegrationTests(unittest.TestCase):
    def test_analysis_response_keeps_explanations_evidence_and_projects(self):
        parsed = {
            "skills": ["Python"], "keywords": ["Python", "REST API"],
            "action_verbs": ["Built"], "professional_summary": "Software developer focused on APIs.",
            "projects": [{"title": "Resume API", "description": "Built a REST API using Python.", "technologies": ["Python"]}],
            "experience": [], "education": [{"degree": "BS", "institution": "Example University", "year": "2024"}],
            "email": None, "phone": None, "linkedin": None, "github": None,
        }
        jd = {"required_skills": ["Docker"], "preferred_skills": [], "keywords": ["Docker"]}
        comparison = {"match_percentage": 50.0, "semantic_similarity": 0.5, "matched_keywords": ["Python"], "missing_keywords": ["Docker"], "skills_gap": ["Docker"]}
        with patch.dict("os.environ", {"GROQ_API_KEY": ""}), \
                patch("backend.services.resume_analyzer.parse_resume", return_value=parsed), \
                patch("backend.services.resume_analyzer.parse_job_description", return_value=jd), \
                patch("backend.services.resume_analyzer.compare_resume_with_jd", return_value=comparison):
            result = analyze_full_resume("Skills\nPython\nProjects\n• Built a REST API using Python.", None, FakeEmbedder(), "Backend role requiring Docker", "Backend Developer")
        response = AnalysisResponse(
            ATS_score=result["ATS_score"], ats_score=result["ats_score"],
            component_scores=ComponentScores(**result["component_scores"]),
            issues_summary=result["issues_summary"], detailed_feedback=result["detailed_feedback"],
            jd_match_analysis=JDComparison(**result["jd_match_analysis"]),
            jd_comparison=JDComparison(**result["jd_comparison"]),
            skill_validation_details=SkillValidationDetails(**result["skill_validation_details"]),
            score_explanations=result["score_explanations"],
            overall_score_explanation=result["overall_score_explanation"],
            project_recommendations=result["project_recommendations"],
            recommendations_source=result["recommendations_source"], target_role=result["target_role"],
            projects=result["projects"], strengths=result["strengths"], suggestions=result["suggestions"],
            critical_issues=result["critical_issues"], interpretation=result["interpretation"],
            skills=result["skills"], matched_keywords=result["matched_keywords"], missing_keywords=result["missing_keywords"],
        )
        self.assertEqual(response.skill_validation_details.skills[0]["classification"], "Demonstrated")
        self.assertEqual(response.skill_validation_details.skills[-1]["classification"], "Not Found")
        self.assertTrue(response.score_explanations)
        self.assertTrue(response.project_recommendations)


class ProjectRecommendationTests(unittest.TestCase):
    def test_fallback_addresses_specific_gap_without_claiming_fake_outcomes(self):
        with patch.dict("os.environ", {"GROQ_API_KEY": ""}):
            result = recommend_projects(
                role="Backend Developer", skills=["Python", "FastAPI"], projects=[],
                skill_details=[{"skill": "Redis", "classification": "Listed Only"}], jd_gaps=["Docker"],
            )
        project = result["recommendations"][0]
        self.assertEqual(result["source"], "fallback")
        self.assertIn("Redis", project["skills_addressed"])
        self.assertIn("Docker", project["skills_addressed"])
        self.assertIn("measured", project["resume_bullet_structure"].lower())
        self.assertTrue(project["implementation_stages"])

    def test_missing_role_uses_fallback_without_an_llm_call(self):
        with patch.dict("os.environ", {"GROQ_API_KEY": "test-key"}), patch("groq.Groq") as groq_client:
            result = recommend_projects("", ["Python"], [], [], [])
        self.assertEqual(result["source"], "fallback")
        groq_client.assert_not_called()

    def test_invalid_llm_output_falls_back_to_valid_project(self):
        class FakeCompletions:
            @staticmethod
            def create(**kwargs):
                return type("Response", (), {"choices": [type("Choice", (), {"message": type("Message", (), {"content": '{"recommendations": [{"title": "Incomplete"}]}'})()})()]})()

        fake_client = type("FakeClient", (), {"chat": type("Chat", (), {"completions": FakeCompletions()})()})()
        with patch.dict("os.environ", {"GROQ_API_KEY": "test-key"}), patch("groq.Groq", return_value=fake_client):
            result = recommend_projects("Backend Developer", ["Python"], [], [{"skill": "Redis", "classification": "Listed Only"}], ["Docker"])
        self.assertEqual(result["source"], "fallback")
        self.assertTrue(result["recommendations"][0]["core_features"])

    def test_groq_api_failure_falls_back(self):
        with patch.dict("os.environ", {"GROQ_API_KEY": "test-key"}), patch("groq.Groq", side_effect=RuntimeError("offline")):
            result = recommend_projects("Backend Developer", ["Python"], [], [], ["Docker"])
        self.assertEqual(result["source"], "fallback")
        self.assertIn("Docker", result["skill_gaps"])

    def test_pdf_html_includes_score_evidence_and_project_recommendation(self):
        reports = generate_html_reports({
            "ats_score": 72,
            "component_scores": {"formatting": 15, "keywords": 18, "content": 18, "skill_validation": 9, "ats_compatibility": 12},
            "score_explanations": [{"category": "Content Quality", "obtained_score": 18, "maximum_score": 25, "reason": "Signals counted", "deductions": [], "suggestions": ["Clarify the action"], "evidence": ["Built a service."]}],
            "overall_score_explanation": {"summary": "Review complete", "strongest_category": "Formatting", "strongest_score": "15/20", "weakest_category": "Skill Validation", "weakest_score": "9/15"},
            "skill_validation_details": {"skills": [{"skill": "Python", "classification": "Demonstrated", "evidence": "Built a service using Python.", "explanation": "Evidence found", "source_section": "Project", "source_name": "API", "recommendation": "Keep the example specific."}]},
            "project_recommendations": [{"title": "Service API", "difficulty": "Intermediate", "description": "Build an API", "relevance": "Addresses a gap", "skills_addressed": ["Docker"], "technologies": ["FastAPI"], "core_features": ["Authentication"], "implementation_stages": ["Build"], "resume_impact": "Shows implementation", "resume_bullet_structure": "[Action] [feature]; verify results."}],
            "target_role": "Backend Developer",
        })
        combined = "\n".join(reports.values())
        self.assertIn("Signals counted", combined)
        self.assertIn("Built a service using Python.", combined)
        self.assertIn("Service API", combined)

    def test_builtin_pdf_fallback_returns_a_readable_pdf(self):
        reports = generate_html_reports({
            "ats_score": 72,
            "component_scores": {"formatting": 15, "keywords": 18, "content": 18, "skill_validation": 9, "ats_compatibility": 12},
            "detailed_feedback": [], "strengths": [], "skill_validation_details": {"skills": []},
        })
        with patch("backend.services.pdf_export._WeasyHTML", None):
            pdf = generate_combined_pdf(reports)
        reader = PdfReader(BytesIO(pdf))
        self.assertTrue(pdf.startswith(b"%PDF-"))
        self.assertGreaterEqual(len(reader.pages), 1)
        extracted = " ".join(page.extract_text() or "" for page in reader.pages)
        self.assertIn("ATS Resume Vision", extracted)
        self.assertIn("Overall ATS Score", extracted)


class PDFEndpointTests(unittest.TestCase):
    def test_backend_pdf_endpoint_returns_pdf_response(self):
        analysis = AnalysisResponse(
            ATS_score=75,
            ats_score=75,
            component_scores=ComponentScores(formatting=15, keywords=18, content=18, skill_validation=12, ats_compatibility=12),
            issues_summary=[],
            detailed_feedback=[],
        )
        endpoint_call = generate_pdf_endpoint(analysis, user_id="test-user")
        try:
            endpoint_call.send(None)
        except StopIteration as result:
            response = result.value
        else:
            self.fail("PDF endpoint unexpectedly awaited external work")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.media_type, "application/pdf")
        self.assertTrue(response.body.startswith(b"%PDF-"))


if __name__ == "__main__":
    unittest.main()
