from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(
        0,
        str(PROJECT_ROOT),
    )


from agent import plan_query
from ranking.job_ranker import rerank_jobs
from ranking.match_quality import classify_match
from ranking.plan_gate import candidate_passes_plan
from ranking.query_parser import parse_query


BASE_DIR = Path(__file__).resolve().parent

REPORT_FILE = (
    BASE_DIR / "offline_benchmark_report.json"
)


def make_job(
    job_id: str,
    title: str,
    skills: list[str] | None = None,
    location: str = "",
    experience: str = "",
    employment_type: str = "",
) -> dict[str, Any]:
    return {
        "job_id": job_id,
        "title": title,
        "company": "Benchmark Company",
        "description": "",
        "search_text": "",
        "skills": skills or [],
        "location": location,
        "experience": experience,
        "employment_type": employment_type,
        "salary": "",
        "url": f"https://example.com/{job_id}",
        "relevance": 1.0,
    }


BENCHMARK_CASES = [
    {
        "id": "react_node_full_stack",
        "query": "React Node.js full stack developer",
        "jobs": [
            {
                "job": make_job(
                    "strong",
                    "Full Stack Developer",
                    ["react", "node.js"],
                ),
                "expected": "strong",
            },
            {
                "job": make_job(
                    "partial",
                    "Applications Developer",
                    ["react"],
                ),
                "expected": "partial",
            },
            {
                "job": make_job(
                    "weak",
                    "Electrical Systems Engineer",
                    ["java", "linux"],
                ),
                "expected": "weak",
            },
        ],
    },
    {
        "id": "java_spring_boot",
        "query": "Java Spring Boot developer",
        "jobs": [
            {
                "job": make_job(
                    "strong",
                    "Java Spring Boot Developer",
                    ["java", "spring boot"],
                ),
                "expected": "strong",
            },
            {
                "job": make_job(
                    "partial",
                    "Java Developer",
                    ["java"],
                ),
                "expected": "partial",
            },
            {
                "job": make_job(
                    "weak",
                    "Electrical Systems Engineer",
                    ["java", "linux"],
                ),
                "expected": "weak",
            },
        ],
    },
    {
        "id": "entry_level_software_engineer",
        "query": "entry level software engineer",
        "jobs": [
            {
                "job": make_job(
                    "strong",
                    "Software Development Engineer Freshers",
                    experience="1+ years of experience",
                ),
                "expected": "strong",
            },
            {
                "job": make_job(
                    "partial",
                    "Software Engineer",
                    experience="5+ years of experience",
                ),
                "expected": "partial",
            },
            {
                "job": make_job(
                    "weak",
                    "Senior Mechanical Engineer",
                    experience="10+ years of experience",
                ),
                "expected": "weak",
            },
        ],
    },
    {
        "id": "remote_software_engineer",
        "query": "software engineer remote",
        "jobs": [
            {
                "job": make_job(
                    "strong",
                    "Software Engineer",
                    location="Remote",
                ),
                "expected": "strong",
            },
            {
                "job": make_job(
                    "partial",
                    "Software Engineer",
                    location="Hybrid",
                ),
                "expected": "partial",
            },
            {
                "job": make_job(
                    "weak",
                    "Marketing Coordinator",
                    location="New York",
                ),
                "expected": "weak",
            },
        ],
    },
    {
        "id": "machine_learning_engineer",
        "query": "machine learning engineer",
        "jobs": [
            {
                "job": make_job(
                    "strong",
                    "Machine Learning Engineer",
                    ["machine learning", "python"],
                ),
                "expected": "strong",
            },
            {
                "job": make_job(
                    "partial",
                    "Python Engineer",
                    ["python"],
                ),
                "expected": "partial",
            },
            {
                "job": make_job(
                    "weak",
                    "Electrical Engineer",
                    ["python"],
                ),
                "expected": "weak",
            },
        ],
    },
]


def evaluate_case(
    case: dict[str, Any],
) -> dict[str, Any]:
    query = case["query"]

    parsed = parse_query(
        query
    )

    plan = plan_query(
        query
    )

    all_jobs = [
        item["job"]
        for item in case["jobs"]
    ]

    expected = {
        item["job"]["job_id"]: item["expected"]
        for item in case["jobs"]
    }

    eligible_jobs: list[
        dict[str, Any]
    ] = []

    gate_results: list[
        dict[str, Any]
    ] = []

    for job in all_jobs:
        keep, reason = (
            candidate_passes_plan(
                job,
                plan,
            )
        )

        gate_results.append(
            {
                "job_id": job["job_id"],
                "title": job["title"],
                "expected_quality": expected[
                    job["job_id"]
                ],
                "eligible": keep,
                "reason": reason,
            }
        )

        if keep:
            eligible_jobs.append(
                job
            )

    ranked = rerank_jobs(
        eligible_jobs,
        parsed,
    )

    ranked_results: list[
        dict[str, Any]
    ] = []

    for rank, job in enumerate(
        ranked,
        start=1,
    ):
        quality = classify_match(
            job,
            parsed,
        )

        ranked_results.append(
            {
                "rank": rank,
                "job_id": job["job_id"],
                "title": job["title"],
                "expected_quality": expected[
                    job["job_id"]
                ],
                "predicted_quality": quality,
                "job_match_score": job.get(
                    "job_match_score",
                    0.0,
                ),
            }
        )

    quality_accuracy = (
        sum(
            result["expected_quality"]
            == result["predicted_quality"]
            for result in ranked_results
        )
        / len(ranked_results)
        if ranked_results
        else 0.0
    )

    expected_strong_id = next(
        (
            job_id
            for job_id, quality
            in expected.items()
            if quality == "strong"
        ),
        None,
    )

    strong_match_first = bool(
        ranked
        and ranked[0]["job_id"]
        == expected_strong_id
    )

    return {
        "query": query,
        "gate_results": gate_results,
        "ranked_results": ranked_results,
        "quality_accuracy": quality_accuracy,
        "strong_match_rank": next(
            (
                result["rank"]
                for result in ranked_results
                if result["job_id"]
                == expected_strong_id
            ),
            None,
        ),
        "strong_match_first": strong_match_first,
    }

def calculate_mrr(
    cases: list[dict[str, Any]],
) -> float:
    reciprocal_ranks: list[float] = []

    for case in cases:
        rank = case.get(
            "strong_match_rank"
        )

        if rank:
            reciprocal_ranks.append(
                1.0 / rank
            )
        else:
            reciprocal_ranks.append(
                0.0
            )

    if not reciprocal_ranks:
        return 0.0

    return sum(
        reciprocal_ranks
    ) / len(reciprocal_ranks)

def calculate_summary(
    cases: list[dict[str, Any]],
) -> dict[str, Any]:
    total_cases = len(cases)

    quality_accuracy = (
        sum(
            case["quality_accuracy"]
            for case in cases
        )
        / total_cases
        if total_cases
        else 0.0
    )

    strong_first = sum(
        case["strong_match_first"]
        for case in cases
    )

    return {
        "total_queries": total_cases,
        "average_quality_accuracy": round(
            quality_accuracy,
            4,
        ),
        "strong_match_first_rate": round(
            (
                strong_first
                / total_cases
                if total_cases
                else 0.0
            ),
            4,
        ),
        "mrr": round(
            calculate_mrr(
                cases
            ),
            4,
        ),
    }

def main() -> None:
    results = [
        evaluate_case(case)
        for case in BENCHMARK_CASES
    ]

    report = {
        "version": "phase-13-v1",
        "offline": True,
        "summary": calculate_summary(
            results
        ),
        "cases": results,
    }

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

    print("=" * 70)
    print("PHASE 13 OFFLINE RANKING BENCHMARK")
    print("=" * 70)

    print(
        "Queries:",
        report["summary"]["total_queries"],
    )

    print(
        "Average quality accuracy:",
        report["summary"][
            "average_quality_accuracy"
        ],
    )

    print(
        "Strong-match-first rate:",
        report["summary"][
            "strong_match_first_rate"
        ],
    )

    print(
        "MRR:",
        report["summary"]["mrr"],
    )

    for case in results:
        print()
        print(
            case["query"]
        )

        for result in case[
            "ranked_results"
        ]:
            print(
                f"  #{result['rank']} "
                f"{result['title']} "
                f"-> "
                f"{result['predicted_quality']}"
            )

    print()
    print(
        "Report saved to:",
        REPORT_FILE,
    )


if __name__ == "__main__":
    main()