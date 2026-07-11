import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile

from backend.api.auth import get_current_user
from backend.models.schemas import AnalysisResponse, ComponentScores, JDComparison, SkillValidationDetails
from backend.utils.file_utils import (
    get_default_grammar_results,
    get_default_location_results,
    get_default_skill_validation_results,
)

logger = logging.getLogger('ats_resume_scorer')

router = APIRouter(prefix='/api/v1', tags=['Analysis'])

def _clean(text: str) -> str:
    for prefix in ('✅', '🌟', '❌', '⚠️', '📝', '🔴', '🟡', '🟢', '🟠', '👍'):
        text = text.lstrip(prefix)
    return text.strip()

@router.post('/analyze-resume', response_model=AnalysisResponse)
async def analyze_resume(
    request: Request,
    resume: UploadFile = File(..., description='Resume file — PDF or DOCX, max 5 MB'),
    job_description: str = Form('', description='Job description text (optional)'),
    user_id: str = Depends(get_current_user),
):

    print("STEP 1: Request received")

    warnings: List[str] = []

    nlp = request.app.state.nlp
    embedder = request.app.state.embedder

    print("STEP 2: Models loaded")

    try:
        print("STEP 3: Reading uploaded file")

        file_bytes = await resume.read()

        filename = resume.filename or 'resume'

        print(f"STEP 4: File name = {filename}")

        from backend.services.resume_parser import (
            FileParsingError,
            FileValidationError,
            parse_resume_file,
        )

        print("STEP 5: Starting resume parsing")

        resume_text, _metadata = parse_resume_file(file_bytes, filename)

        print("STEP 6: Resume parsing completed")

        print(f"STEP 7: Resume text length = {len(resume_text)}")

        logger.info(f"Parsed '{filename}': {len(resume_text)} chars extracted")

    except Exception as exc:

        print("ERROR DURING FILE PARSING")
        print(exc)

        logger.error(f'File parsing failed: {exc}')

        raise HTTPException(
            status_code=422,
            detail=f'Could not read or parse the resume: {exc}',
        )

    try:

        print("STEP 8: Importing analyzer")

        from backend.services.resume_analyzer import analyze_full_resume

        print("STEP 9: Starting full AI analysis")

        result = analyze_full_resume(
            resume_text=resume_text,
            nlp=nlp,
            embedder=embedder,
            job_description=job_description
        )

        print("STEP 10: AI analysis completed")

    except Exception as exc:

        print("ERROR DURING ANALYSIS")
        print(exc)

        logger.error(f'Full analysis pipeline failed: {exc}')

        raise HTTPException(
            status_code=500,
            detail=f'Analysis pipeline failed: {exc}'
        )

    print("STEP 11: Preparing JD comparison")

    jd_comparison_result = None

    if result.get('jd_comparison'):

        jd_comparison_result = JDComparison(
            match_percentage=round(float(result['jd_comparison'].get('match_percentage', 0.0)), 1),
            semantic_similarity=round(float(result['jd_comparison'].get('semantic_similarity', 0.0)), 3),
            matched_keywords=result['jd_comparison'].get('matched_keywords', [])[:20],
            missing_keywords=result['jd_comparison'].get('missing_keywords', [])[:15],
            skills_gap=result['jd_comparison'].get('skills_gap', [])[:10],
        )

    print("STEP 12: Preparing skill validation")

    detailed_fb = result.get('detailed_feedback', [])

    svd_raw = result.get('skill_validation_details') or {}

    skill_val_details = SkillValidationDetails(
        validated=svd_raw.get('validated', []),
        unvalidated=svd_raw.get('unvalidated', []),
        total=svd_raw.get('total', 0),
        validated_count=svd_raw.get('validated_count', 0),
        validation_pct=svd_raw.get('validation_pct', 0.0),
    )

    print("STEP 13: Creating response object")

    response = AnalysisResponse(
        ATS_score=result['ats_score'],
        component_scores=ComponentScores(**result['component_scores']),
        issues_summary=result['issues_summary'],
        detailed_feedback=detailed_fb,
        jd_match_analysis=jd_comparison_result,
        skill_validation_details=skill_val_details,

        ats_score=result['ats_score'],
        keyword_match=jd_comparison_result.match_percentage if jd_comparison_result else 0.0,
        missing_keywords=result.get('missing_keywords', []),
        matched_keywords=result.get('matched_keywords', []),
        skills=list(result.get('skills', [])[:20]),
        jd_comparison=jd_comparison_result,
        interpretation=result.get('interpretation', '')
    )

    print("STEP 14: Saving analysis to database")

    try:

        from backend.database.supabase_db import save_analysis

        await save_analysis(user_id, filename, result)

        print("STEP 15: Database save successful")

    except Exception as exc:

        print("DATABASE SAVE FAILED")
        print(exc)

        logger.warning(f'History save failed (non-blocking): {exc}')

    print("STEP 16: Returning final response")

    return response

@router.get('/health')
async def health_check(request: Request):
    """Health check — confirms models are loaded and the API is ready."""
    return {
        'status':          'healthy',
        'nlp_loaded':      request.app.state.nlp is not None,
        'embedder_loaded': request.app.state.embedder is not None,
    }

@router.get('/history')
async def get_history(user_id: str = Depends(get_current_user)):
    """Return the signed-in user's past analyses (identity comes from the JWT)."""
    from backend.database.supabase_db import get_user_history
    try:
        return await get_user_history(user_id)
    except Exception as exc:
        logger.error(f'History fetch failed: {exc}')
        raise HTTPException(status_code=500, detail=f'Could not load history: {exc}')


@router.delete('/history/{analysis_id}')
async def delete_history_entry(
    analysis_id: str,
    user_id: str = Depends(get_current_user),
):
    """Delete one analysis from the signed-in user's history."""
    from backend.database.supabase_db import delete_analysis
    try:
        success = await delete_analysis(analysis_id, user_id)
        if not success:
            raise HTTPException(status_code=404, detail='Analysis not found or not owned by this user.')
        return {'status': 'deleted', 'id': analysis_id}
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f'History delete failed: {exc}')
        raise HTTPException(status_code=500, detail=f'Could not delete: {exc}')
    

@router.post('/generate-pdf')
async def generate_pdf(
    data: AnalysisResponse,
    user_id: str = Depends(get_current_user),
):
    from backend.services.report_generator import generate_html_reports
    from backend.services.pdf_export import generate_combined_pdf
    from fastapi.responses import Response

    try:
        html_docs = generate_html_reports(data.model_dump())
        pdf_bytes = generate_combined_pdf(html_docs)

        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": "attachment; filename=ats_report.pdf"
            }
        )
    except Exception as e:
        logger.error(f'Failed to generate PDF: {e}')
        raise HTTPException(status_code=500, detail=f"Failed to generate PDF: {e}")
    

@router.get('/history/{analysis_id}/pdf')
async def generate_history_pdf(
    analysis_id: str,
    user_id: str = Depends(get_current_user),
):
    from backend.database.supabase_db import get_user_history
    from backend.services.report_generator import generate_html_reports
    from backend.services.pdf_export import generate_combined_pdf
    from fastapi.responses import Response

    history = await get_user_history(user_id)
    analysis_data = next((item["analysis_result"] for item in history if item["id"] == analysis_id), None)

    if not analysis_data:
        raise HTTPException(status_code=404, detail="Analysis not found")

    try:
        html_docs = generate_html_reports(analysis_data)
        pdf_bytes = generate_combined_pdf(html_docs)

        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename=ats_report_{analysis_id}.pdf"
            }
        )
    except Exception as e:
        logger.error(f'Failed to generate PDF for history: {e}')
        raise HTTPException(status_code=500, detail=f"Failed to generate PDF: {e}")