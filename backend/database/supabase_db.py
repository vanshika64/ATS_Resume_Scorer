import logging
import httpx
import json
from datetime import datetime, timezone
from typing import Optional, List, Dict

logger = logging.getLogger("ats_resume_logger")
from backend.core.config import SUPABASE_URL, SUPABASE_KEY

def get_headers():
    if not SUPABASE_KEY or not SUPABASE_URL:
        return None
    return {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=representation"
    }

async def save_analysis(user_id: str,filename: str,analysis_result: Dict
) -> Optional[str]:
    headers = get_headers()
    if not headers:
        return None
    def _json_default(o):
        if hasattr(o, "model_dump"):
            return o.model_dump()
        return str(o)
    serializable_result = json.loads(
        json.dumps(
            analysis_result,
            default=_json_default
        )
    )

    doc = {
        "user_id": user_id,
        "filename": filename,
        "ats_score": serializable_result.get("ats_score", 0),
        "keyword_match": serializable_result.get("keyword_match", 0),
        "missing_keywords": serializable_result.get(
            "missing_keywords",
            []
        ),
        "created_at": datetime.now(
            timezone.utc
        ).isoformat(),
        "analysis_result": serializable_result,
    }
    url = f"{SUPABASE_URL.rstrip('/')}/rest/v1/analyses"
    try:
        async with httpx.AsyncClient() as client:

            response = await client.post(url,headers=headers,json=doc)
            response.raise_for_status()
            data = response.json()
            if data and len(data) > 0:

                inserted_id = str(data[0].get("id"))
                logger.info(
                    f"Saved analysis for user "
                    f"{user_id}: {inserted_id}"
                )
                return inserted_id
            return None

    except Exception as exc:
        logger.error(
            f"Failed to save analysis "
            f"to Supabase: {exc}"
        )
        return None

async def get_user_history(user_id: str) -> List[Dict]:
    headers = get_headers()

    if not headers:
        return []
    url = (
        f"{SUPABASE_URL.rstrip('/')}/rest/v1/analyses"
        f"?user_id=eq.{user_id}"
        f"&order=created_at.desc"
    )
    try:

        async with httpx.AsyncClient() as client:
            response = await client.get(
                url,
                headers=headers
            )
            response.raise_for_status()

            documents = response.json()

        results = []
        for doc in documents:

            results.append({
                "id": str(doc.get("id")),
                "filename": doc.get(
                    "filename",
                    "resume"
                ),
                "resume_name": doc.get(
                    "filename",
                    "resume"
                ),
                "job_title": "Software Engineer",
                "ats_score": doc.get(
                    "ats_score",
                    0
                ),
                "keyword_match": doc.get(
                    "keyword_match",
                    0
                ),
                "missing_keywords": doc.get(
                    "missing_keywords",
                    []
                ),
                "date": doc.get(
                    "created_at",
                    ""
                ),
                "created_at": doc.get(
                    "created_at",
                    ""
                ),
                "analysis_result": doc.get(
                    "analysis_result",
                    {}
                ),
            })

        return results

    except Exception as exc:

        logger.error(
            f"Failed to fetch history "
            f"from Supabase: {exc}"
        )

        return []


async def delete_analysis(
    analysis_id: str,
    user_id: str
) -> bool:

    headers = get_headers()

    if not headers:
        return False

    url = (
        f"{SUPABASE_URL.rstrip('/')}/rest/v1/analyses"
        f"?id=eq.{analysis_id}"
        f"&user_id=eq.{user_id}"
    )

    try:
        async with httpx.AsyncClient() as client:
            response = await client.delete(
                url,
                headers=headers
            )
            response.raise_for_status()
            logger.info(
                f"Deleted analysis "
                f"{analysis_id} "
                f"for user {user_id}"
            )

            return True

    except Exception as exc:

        logger.error(
            f"Failed to delete analysis "
            f"from Supabase: {exc}"
        )

        return False