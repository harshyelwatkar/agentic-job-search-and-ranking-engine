from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from agent import plan_query
from agent_search import execute_search_plan
from ranking.search_explanation import summarize_search


# ============================================================
# Paths
# ============================================================

BASE_DIR = Path(__file__).resolve().parent

UI_ASSETS_DIR = BASE_DIR / "ui_assets"

INDEX_HTML = UI_ASSETS_DIR / "index.html"


# ============================================================
# FastAPI application
# ============================================================

app = FastAPI(
    title="Agentic Job Search",
    description=(
        "Agentic job search UI backed by Vespa Cloud, "
        "query planning, relevance gating, "
        "job-specific reranking, and search explanations."
    ),
)


app.mount(
    "/assets",
    StaticFiles(
        directory=str(UI_ASSETS_DIR)
    ),
    name="assets",
)


# ============================================================
# Search request
# ============================================================

class SearchRequest(BaseModel):
    query: str = Field(
        ...,
        min_length=1,
        max_length=500,
    )


# ============================================================
# Helpers
# ============================================================

def _serialize_job(
    job: dict[str, Any],
) -> dict[str, Any]:
    """
    Convert the internal ranking result into a JSON-safe
    response object for the frontend.
    """

    features = job.get(
        "ranking_features",
        {},
    ) or {}

    return {
        "rank": job.get(
            "final_rank",
            0,
        ),
        "job_id": job.get(
            "job_id"
        ),
        "title": job.get(
            "title"
        ),
        "company": job.get(
            "company"
        ),
        "description": job.get(
            "description"
        ),
        "skills": job.get(
            "skills"
        ) or [],
        "location": job.get(
            "location"
        ),
        "experience": job.get(
            "experience"
        ),
        "employment_type": job.get(
            "employment_type"
        ),
        "salary": job.get(
            "salary"
        ),
        "url": job.get(
            "url"
        ),
        "relevance": job.get(
            "relevance",
            0.0,
        ),
        "job_match_score": job.get(
            "job_match_score",
            0.0,
        ),
        "match_quality": job.get(
            "match_quality",
            "unknown",
        ),
        "plan_gate_reason": job.get(
            "plan_gate_reason"
        ),
        "matched_skills": features.get(
            "matched_skills",
            [],
        ),
        "missing_skills": features.get(
            "missing_skills",
            [],
        ),
        "title_score": features.get(
            "title",
            0.0,
        ),
        "skill_score": features.get(
            "skills",
            0.0,
        ),
        "experience_score": features.get(
            "experience",
            0.0,
        ),
        "location_score": features.get(
            "location",
            0.0,
        ),
        "employment_score": features.get(
            "employment",
            0.0,
        ),
    }


def _build_plan_response(
    plan: Any,
) -> dict[str, Any]:
    """
    Convert SearchPlan into a frontend-friendly dictionary.
    """

    return {
        "role_terms": list(
            plan.role_terms
        ),
        "skills": list(
            plan.skills
        ),
        "locations": list(
            plan.locations
        ),
        "experience_years": (
            plan.experience_years
        ),
        "entry_level": bool(
            plan.entry_level
        ),
        "senior_level": bool(
            plan.senior_level
        ),
        "employment_types": list(
            plan.employment_types
        ),
        "retrieval_mode": (
            plan.retrieval_mode
        ),
        "requires_skill_matching": bool(
            plan.requires_skill_matching
        ),
        "requires_location_matching": bool(
            plan.requires_location_matching
        ),
        "requires_experience_matching": bool(
            plan.requires_experience_matching
        ),
        "gate_mode": plan.gate_mode,
        "minimum_skill_coverage": (
            plan.minimum_skill_coverage
        ),
        "require_location_match": bool(
            plan.require_location_match
        ),
        "require_experience_match": bool(
            plan.require_experience_match
        ),
    }


# ============================================================
# Routes
# ============================================================

@app.get(
    "/",
    response_class=HTMLResponse,
)
def index() -> str:
    """
    Serve the frontend application.
    """

    if not INDEX_HTML.exists():
        raise HTTPException(
            status_code=500,
            detail=(
                "Frontend index.html was not found at: "
                f"{INDEX_HTML}"
            ),
        )

    return INDEX_HTML.read_text(
        encoding="utf-8"
    )


@app.get("/api/health")
def health() -> dict[str, str]:
    """
    Simple backend health endpoint.
    """

    return {
        "status": "ok",
        "service": "agentic-job-search",
    }


@app.post("/api/search")
def search(
    payload: SearchRequest,
) -> dict[str, Any]:
    """
    Run the complete Phase 12 agentic search pipeline.

    Flow:

        User query
            ↓
        Query planner
            ↓
        Retrieval strategy
            ↓
        Vespa retrieval
            ↓
        Plan-aware gate
            ↓
        Job reranking
            ↓
        Match quality
            ↓
        Search explanation
    """

    query = payload.query.strip()

    if not query:
        raise HTTPException(
            status_code=422,
            detail="Search query cannot be empty.",
        )

    try:
        # ----------------------------------------------------
        # 1. Build search plan
        # ----------------------------------------------------

        plan = plan_query(
            query
        )

        # ----------------------------------------------------
        # 2. Execute agentic search
        # ----------------------------------------------------

        jobs = execute_search_plan(
            plan,
            hits=100,
        )

        # ----------------------------------------------------
        # 3. Build explanation
        # ----------------------------------------------------

        explanation = summarize_search(
            query,
            jobs,
        )

        # ----------------------------------------------------
        # 4. Use a fixed frontend result limit
        # ----------------------------------------------------

        visible_jobs = jobs[:10]

        results = [
            _serialize_job(job)
            for job in visible_jobs
        ]

        # ----------------------------------------------------
        # 5. Frontend response
        # ----------------------------------------------------

        return {
            "query": query,

            "results": results,

            "totalCount": len(
                jobs
            ),

            "plan": _build_plan_response(
                plan
            ),

            "summary": {
                "text": explanation.get(
                    "summary",
                    "",
                ),
                "strong_matches": explanation.get(
                    "strong_matches",
                    0,
                ),
                "partial_matches": explanation.get(
                    "partial_matches",
                    0,
                ),
                "weak_matches": explanation.get(
                    "weak_matches",
                    0,
                ),
            },

            "best_match": explanation.get(
                "best_job"
            ),
        }

    except HTTPException:
        raise

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=(
                "Agentic search failed: "
                f"{type(exc).__name__}: {exc}"
            ),
        ) from exc