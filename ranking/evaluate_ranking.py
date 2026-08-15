from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


# Add project root to Python's import path.
PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from job_search import search
from ranking.query_parser import parse_query


BASE_DIR = Path(__file__).resolve().parent

QUERY_FILE = BASE_DIR / "test_queries.json"
REPORT_FILE = BASE_DIR / "ranking_report.json"


def load_queries() -> list[dict[str, Any]]:
    with QUERY_FILE.open(
        "r",
        encoding="utf-8",
    ) as file:
        data = json.load(file)

    return data["queries"]


def print_result(
    rank: int,
    job: dict[str, Any],
) -> None:

    features = job.get(
        "ranking_features",
        {},
    )

    print()
    print(
        f"#{rank} "
        f"{job.get('title') or 'Untitled'}"
    )

    print(
        "Company:",
        job.get("company") or "N/A",
    )

    print(
        "Skills:",
        job.get("skills") or "N/A",
    )

    print(
        "Location:",
        job.get("location") or "N/A",
    )

    print(
        "Experience:",
        job.get("experience") or "N/A",
    )

    print(
        "Employment:",
        job.get("employment_type") or "N/A",
    )

    print(
        "Vespa relevance:",
        job.get("relevance"),
    )

    print(
        "Job-match score:",
        job.get("job_match_score"),
    )

    print(
        "Relevance gate:",
        job.get(
            "relevance_gate_reason",
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
        job.get("url"),
    )


def main() -> None:

    queries = load_queries()

    report: dict[str, Any] = {
        "version": "phase-11-v3-relevance-gate",
        "instance": "jobs-clean",
        "candidate_retrieval_hits": 50,
        "queries": {},
    }

    print("=" * 75)
    print(
        "PHASE 11 JOB-SPECIFIC RANKING "
        "WITH RELEVANCE GATE"
    )
    print("=" * 75)

    for index, query_def in enumerate(
        queries,
        start=1,
    ):

        query_id = query_def["id"]
        query = query_def["query"]

        parsed = parse_query(
            query
        )

        print()
        print("=" * 75)
        print(
            f"QUERY {index}/{len(queries)}"
        )
        print(
            query_id,
            ":",
            query,
        )
        print("=" * 75)

        print(
            "Roles:",
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

        results = search(
            query=query,
            ranking="hybrid",
            hits=50,
        )

        print()
        print(
            "Eligible results returned:",
            len(results),
        )

        query_report: dict[str, Any] = {
            "query": query,
            "parsed": {
                "role_terms": parsed.role_terms,
                "skills": parsed.skills,
                "locations": parsed.locations,
                "experience_years": parsed.experience_years,
                "employment_types": parsed.employment_types,
                "entry_level": parsed.entry_level,
                "senior_level": parsed.senior_level,
            },
            "results": [],
        }

        for rank, job in enumerate(
            results[:10],
            start=1,
        ):

            print_result(
                rank,
                job,
            )

            features = job.get(
                "ranking_features",
                {},
            )

            query_report[
                "results"
            ].append(
                {
                    "rank": rank,
                    "title": job.get(
                        "title"
                    ),
                    "company": job.get(
                        "company"
                    ),
                    "location": job.get(
                        "location"
                    ),
                    "experience": job.get(
                        "experience"
                    ),
                    "employment_type": job.get(
                        "employment_type"
                    ),
                    "url": job.get(
                        "url"
                    ),
                    "job_match_score": job.get(
                        "job_match_score"
                    ),
                    "vespa_relevance": job.get(
                        "relevance"
                    ),
                    "relevance_gate_reason": job.get(
                        "relevance_gate_reason"
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
            )

        report[
            "queries"
        ][query_id] = query_report

    with REPORT_FILE.open(
        "w",
        encoding="utf-8",
    ) as file:

        json.dump(
            report,
            file,
            indent=2,
            ensure_ascii=False,
        )

    print()
    print("=" * 75)
    print(
        "Ranking evaluation saved to:"
    )
    print(REPORT_FILE)
    print("=" * 75)


if __name__ == "__main__":
    main()