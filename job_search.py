from __future__ import annotations

from typing import Any

from vespa.deployment import VespaCloud
from vespa.package import ApplicationPackage

from ranking.job_ranker import rerank_jobs
from ranking.match_quality import classify_match
from ranking.plan_gate import candidate_passes_plan
from ranking.query_parser import parse_query


TENANT = "agentic-search"
APPLICATION = "agenticjobsearch"
INSTANCE = "jobs-clean"

DEFAULT_RANKING = "hybrid"

RANKING_PROFILES = {
    "bm25": "bm25",
    "semantic": "semantic",
    "hybrid": "hybrid",
    "rrf": "rrf",
}


def get_app() -> Any:
    package = ApplicationPackage(
        name=APPLICATION
    )

    vespa = VespaCloud(
        tenant=TENANT,
        application=APPLICATION,
        application_package=package,
    )

    return vespa.get_application(
        instance=INSTANCE
    )


def build_query_body(
    query: str,
    ranking: str,
    hits: int,
) -> dict[str, Any]:

    profile = RANKING_PROFILES.get(
        ranking,
        DEFAULT_RANKING,
    )

    if profile == "bm25":
        return {
            "yql": (
                "select * from job "
                "where userQuery();"
            ),
            "query": query,
            "ranking": profile,
            "hits": hits,
        }

    nearest_neighbor = (
        "({targetHits:100}"
        "nearestNeighbor(text_embedding,q))"
    )

    if profile == "semantic":
        yql = (
            "select * from job "
            f"where {nearest_neighbor}"
        )
    else:
        yql = (
            "select * from job "
            f"where userQuery() "
            f"or {nearest_neighbor}"
        )

    return {
        "yql": yql,
        "query": query,
        "ranking": profile,
        "input.query(q)": (
            f'embed(e5, "query: {query}")'
        ),
        "hits": hits,
    }


def _extract_jobs(
    data: dict[str, Any],
) -> list[dict[str, Any]]:
    children = (
        data
        .get("root", {})
        .get("children", [])
        or []
    )

    jobs: list[dict[str, Any]] = []

    for rank, hit in enumerate(
        children,
        start=1,
    ):
        fields = hit.get(
            "fields",
            {},
        ) or {}

        jobs.append(
            {
                "rank": rank,
                "job_id": fields.get(
                    "job_id"
                ),
                "title": fields.get(
                    "title"
                ),
                "company": fields.get(
                    "company"
                ),
                "description": fields.get(
                    "description"
                ),
                "search_text": fields.get(
                    "search_text"
                ),
                "skills": fields.get(
                    "skills"
                ),
                "location": fields.get(
                    "location"
                ),
                "experience": fields.get(
                    "experience"
                ),
                "employment_type": fields.get(
                    "employment_type"
                ),
                "salary": fields.get(
                    "salary"
                ),
                "url": fields.get(
                    "url"
                ),
                "relevance": hit.get(
                    "relevance",
                    0.0,
                ),
            }
        )

    return jobs


def search(
    query: str,
    ranking: str = DEFAULT_RANKING,
    hits: int = 100,
) -> list[dict[str, Any]]:

    cleaned_query = query.strip()

    if not cleaned_query:
        return []

    app = get_app()

    parsed = parse_query(
        cleaned_query
    )

    response = app.query(
        body=build_query_body(
            query=cleaned_query,
            ranking=ranking,
            hits=hits,
        )
    )

    data = response.get_json()

    jobs = _extract_jobs(
        data
    )

    # ========================================================
    # Stage 1:
    # Plan-aware candidate gating
    # ========================================================

    eligible_jobs: list[
        dict[str, Any]
    ] = []

    for job in jobs:

        keep, reason = (
            candidate_passes_plan(
                job,
                _build_search_plan_from_query(
                    parsed
                ),
            )
        )

        job["plan_gate"] = {
            "eligible": keep,
            "reason": reason,
        }

        if keep:
            eligible_jobs.append(
                job
            )

    # ========================================================
    # Stage 2:
    # Job-specific reranking
    # ========================================================

    reranked = rerank_jobs(
        eligible_jobs,
        parsed,
    )

    # ========================================================
    # Stage 3:
    # Match-quality classification
    # ========================================================

    for final_rank, job in enumerate(
        reranked,
        start=1,
    ):
        job["final_rank"] = final_rank

        gate = job.get(
            "plan_gate",
            {},
        )

        job["plan_gate_reason"] = (
            gate.get("reason")
        )

        job["match_quality"] = (
            classify_match(
                job,
                parsed,
            )
        )

    return reranked


def _build_search_plan_from_query(
    parsed: Any,
):
    """
    Build a lightweight SearchPlan-compatible object
    from a parsed query for the legacy search() API.

    The Phase 12 agentic entry point uses agent.plan_query()
    directly. This helper keeps job_search.search() compatible
    with the existing API and test infrastructure.
    """

    from agent import plan_query

    return plan_query(
        parsed.raw_query
    )


def main() -> None:

    query = input(
        "Enter job search query: "
    ).strip()

    if not query:
        print(
            "Query cannot be empty."
        )
        return

    parsed = parse_query(
        query
    )

    print()
    print("=" * 75)
    print("PARSED QUERY")
    print("=" * 75)

    print(
        "Role terms:",
        parsed.role_terms or "none",
    )

    print(
        "Skills:",
        parsed.skills or "none",
    )

    print(
        "Locations:",
        parsed.locations or "none",
    )

    print(
        "Experience:",
        parsed.experience_years
        if parsed.experience_years is not None
        else "none",
    )

    print(
        "Entry level:",
        parsed.entry_level,
    )

    print(
        "Senior level:",
        parsed.senior_level,
    )

    print(
        "Employment:",
        parsed.employment_types or "none",
    )

    print()
    print("=" * 75)
    print(
        "RETRIEVAL + PLAN GATE + "
        "RERANKING + MATCH QUALITY"
    )
    print("=" * 75)

    results = search(
        query=query,
        ranking="hybrid",
        hits=100,
    )

    print(
        "Final eligible results:",
        len(results),
    )

    if not results:
        print()
        print(
            "No candidates passed the "
            "current search plan."
        )
        return

    for job in results[:10]:

        features = job.get(
            "ranking_features",
            {},
        )

        print()
        print(
            f"#{job['final_rank']} "
            f"{job.get('title') or 'Untitled'}"
        )

        print(
            "Company:",
            job.get("company")
            or "N/A",
        )

        print(
            "Skills:",
            job.get("skills")
            or "N/A",
        )

        print(
            "Location:",
            job.get("location")
            or "N/A",
        )

        print(
            "Experience:",
            job.get("experience")
            or "N/A",
        )

        print(
            "Employment:",
            job.get("employment_type")
            or "N/A",
        )

        print(
            "Vespa relevance:",
            job.get("relevance"),
        )

        print(
            "Job-match score:",
            job.get(
                "job_match_score"
            ),
        )

        print(
            "Match quality:",
            job.get(
                "match_quality",
                "unknown",
            ),
        )

        print(
            "Plan gate:",
            job.get(
                "plan_gate_reason",
                "N/A",
            ),
        )

        print(
            "Matched skills:",
            features.get(
                "matched_skills",
                [],
            ),
        )

        print(
            "Missing skills:",
            features.get(
                "missing_skills",
                [],
            ),
        )

        print(
            "Title score:",
            features.get(
                "title",
                0.0,
            ),
        )

        print(
            "Skill score:",
            features.get(
                "skills",
                0.0,
            ),
        )

        print(
            "Experience score:",
            features.get(
                "experience",
                0.0,
            ),
        )

        print(
            "Location score:",
            features.get(
                "location",
                0.0,
            ),
        )

        print(
            "Employment score:",
            features.get(
                "employment",
                0.0,
            ),
        )

        print(
            "URL:",
            job.get("url")
        )


if __name__ == "__main__":
    main()