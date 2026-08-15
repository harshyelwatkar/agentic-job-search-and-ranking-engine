from __future__ import annotations

from typing import Any

from agent import (
    SearchPlan,
    plan_query,
    print_search_plan,
)
from job_search import (
    _extract_jobs,
    build_query_body,
    get_app,
)
from ranking.job_ranker import rerank_jobs
from ranking.match_quality import classify_match
from ranking.plan_gate import candidate_passes_plan
from ranking.search_explanation import (
    print_search_explanation,
)


def _parsed_query_from_plan(
    plan: SearchPlan,
):
    """
    Convert the Phase 12 SearchPlan back into the ParsedQuery
    object expected by the existing ranking components.
    """

    from ranking.query_parser import ParsedQuery

    return ParsedQuery(
        raw_query=plan.raw_query,
        role_terms=list(
            plan.role_terms
        ),
        skills=list(
            plan.skills
        ),
        locations=list(
            plan.locations
        ),
        experience_years=(
            plan.experience_years
        ),
        employment_types=list(
            plan.employment_types
        ),
        entry_level=plan.entry_level,
        senior_level=plan.senior_level,
    )


def execute_search_plan(
    plan: SearchPlan,
    hits: int = 100,
) -> list[dict[str, Any]]:
    """
    Execute a Phase 12 SearchPlan.

    Pipeline:

        SearchPlan
            ↓
        Vespa retrieval
            ↓
        Plan-aware candidate gate
            ↓
        Python reranking
            ↓
        Match-quality classification
            ↓
        Explanation generation
    """

    app = get_app()

    response = app.query(
        body=build_query_body(
            query=plan.raw_query,
            ranking=plan.retrieval_mode,
            hits=hits,
        )
    )

    data = response.get_json()

    jobs = _extract_jobs(
        data
    )

    eligible: list[
        dict[str, Any]
    ] = []

    rejected: list[
        dict[str, Any]
    ] = []

    # Build this once rather than reconstructing it for every job.
    parsed_query = _parsed_query_from_plan(
        plan
    )

    # --------------------------------------------------------
    # Plan-aware candidate gating
    # --------------------------------------------------------

    for job in jobs:

        keep, reason = (
            candidate_passes_plan(
                job,
                plan,
            )
        )

        job_copy = dict(job)

        job_copy[
            "plan_gate"
        ] = {
            "eligible": keep,
            "reason": reason,
        }

        if keep:
            eligible.append(
                job_copy
            )
        else:
            rejected.append(
                job_copy
            )

    # --------------------------------------------------------
    # Job-specific reranking
    # --------------------------------------------------------

    reranked = rerank_jobs(
        eligible,
        parsed_query,
    )

    # --------------------------------------------------------
    # Final metadata
    # --------------------------------------------------------

    for final_rank, job in enumerate(
        reranked,
        start=1,
    ):

        job["final_rank"] = (
            final_rank
        )

        job["match_quality"] = (
            classify_match(
                job,
                parsed_query,
            )
        )

        job["plan_gate_reason"] = (
            job.get(
                "plan_gate",
                {},
            ).get(
                "reason"
            )
        )

    # --------------------------------------------------------
    # Execution diagnostics
    # --------------------------------------------------------

    print(
        f"\nRetrieved candidates: "
        f"{len(jobs)}"
    )

    print(
        f"Plan-eligible candidates: "
        f"{len(eligible)}"
    )

    print(
        f"Plan-rejected candidates: "
        f"{len(rejected)}"
    )

    return reranked


def print_results(
    results: list[dict[str, Any]],
    limit: int = 10,
) -> None:
    """
    Print ranked jobs in a readable terminal format.
    """

    for job in results[:limit]:

        features = job.get(
            "ranking_features",
            {},
        )

        print()
        print(
            f"#{job.get('final_rank', '?')} "
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
                "unknown",
            ),
        )

        print(
            "Job-match score:",
            job.get(
                "job_match_score"
            ),
        )

        print(
            "Vespa relevance:",
            job.get(
                "relevance"
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
            job.get("url"),
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

    try:
        plan = plan_query(
            query
        )
    except ValueError as exc:
        print(
            f"Error: {exc}"
        )
        return

    print_search_plan(
        plan
    )

    print()
    print("=" * 75)
    print("PLAN-AWARE AGENTIC SEARCH")
    print("=" * 75)

    results = execute_search_plan(
        plan,
        hits=100,
    )

    if not results:
        print()
        print(
            "No jobs satisfied the "
            "current search plan."
        )

        # Still provide an explanation so that the system
        # clearly communicates why there is no result set.
        print_search_explanation(
            plan.raw_query,
            results,
        )

        return

    print(
        f"\nFinal results: "
        f"{len(results)}"
    )

    print_results(
        results,
        limit=10,
    )

    print_search_explanation(
        plan.raw_query,
        results,
    )


if __name__ == "__main__":
    main()