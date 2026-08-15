from __future__ import annotations

import sys
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from agent import plan_query
from ranking.job_ranker import rerank_jobs
from ranking.match_quality import classify_match
from ranking.plan_gate import candidate_passes_plan
from ranking.query_parser import parse_query
from ranking.search_explanation import summarize_search


def make_job(
    title: str,
    skills: list[str] | None = None,
    location: str = "",
    experience: str = "",
    employment_type: str = "",
    description: str = "",
) -> dict[str, Any]:
    return {
        "job_id": f"test-{title}",
        "title": title,
        "company": "Test Company",
        "description": description,
        "search_text": description,
        "skills": skills or [],
        "location": location,
        "experience": experience,
        "employment_type": employment_type,
        "salary": "",
        "url": "https://example.com/job",
        "relevance": 1.0,
    }


def assert_parser() -> None:
    cases = {
        "React Node.js full stack developer": {
            "roles": ["full stack developer"],
            "skills": ["node.js", "react"],
        },
        "Java Spring Boot developer": {
            "roles": ["java developer"],
            "skills": ["spring boot", "java"],
        },
        "data engineer SQL": {
            "roles": ["data engineer"],
            "skills": ["sql"],
        },
        "entry level software engineer": {
            "roles": ["software engineer"],
            "skills": [],
        },
        "software engineer remote": {
            "roles": ["software engineer"],
            "skills": [],
        },
    }

    for query, expected in cases.items():
        parsed = parse_query(query)

        assert parsed.role_terms == expected["roles"], (
            f"Role parsing failed for: {query}\n"
            f"Expected: {expected['roles']}\n"
            f"Actual:   {parsed.role_terms}"
        )

        assert parsed.skills == expected["skills"], (
            f"Skill parsing failed for: {query}\n"
            f"Expected: {expected['skills']}\n"
            f"Actual:   {parsed.skills}"
        )

    print("PASS: parser tests")


def assert_role_and_skill_gating() -> None:
    plan = plan_query(
        "Java Spring Boot developer"
    )

    unrelated = make_job(
        title="Electrical Systems Engineer",
        skills=["java", "linux"],
    )

    keep, reason = candidate_passes_plan(
        unrelated,
        plan,
    )

    assert not keep, (
        "Unrelated Electrical Systems Engineer "
        "must not pass Java Spring Boot developer gate"
    )

    print("PASS: role + skill gating")


def assert_partial_skill_match() -> None:
    plan = plan_query(
        "React Node.js full stack developer"
    )

    partial_job = make_job(
        title="Trainee Applications Developer",
        skills=["react", "python"],
    )

    keep, reason = candidate_passes_plan(
        partial_job,
        plan,
    )

    assert keep, (
        "A React partial match should remain "
        "eligible under the current normal-mode policy"
    )

    assert (
        "skill" in reason
        or "role" in reason
    ), (
        "Expected a structured role/skill gate reason, "
        f"got: {reason}"
    )

    print("PASS: partial skill match")


def assert_strong_match() -> None:
    query = "machine learning engineer"

    parsed = parse_query(query)
    plan = plan_query(query)

    strong_job = make_job(
        title="Machine Learning Engineer",
        skills=["machine learning"],
    )

    keep, reason = candidate_passes_plan(
        strong_job,
        plan,
    )

    assert keep, (
        "A genuine machine learning engineer "
        "should pass"
    )

    ranked = rerank_jobs(
        [strong_job],
        parsed,
    )

    assert ranked, (
        "Strong candidate should be reranked"
    )

    quality = classify_match(
        ranked[0],
        parsed,
    )

    assert quality == "strong", (
        f"Expected strong, got {quality}"
    )

    print("PASS: strong match")


def assert_entry_level() -> None:
    query = "entry level software engineer"

    plan = plan_query(query)

    entry_job = make_job(
        title=(
            "Software Development "
            "Engineer Freshers"
        ),
        experience="1+ years of experience",
    )

    keep, reason = candidate_passes_plan(
        entry_job,
        plan,
    )

    assert keep, (
        "Entry-level software engineer "
        "should pass"
    )

    print("PASS: entry-level query")


def assert_remote_constraint() -> None:
    query = "software engineer remote"

    plan = plan_query(query)

    remote_job = make_job(
        title="Software Engineer",
        location="Remote",
    )

    keep, reason = candidate_passes_plan(
        remote_job,
        plan,
    )

    assert keep, (
        "Remote software engineer "
        "should pass"
    )

    print("PASS: remote constraint")


def assert_explanation() -> None:
    query = "React Node.js full stack developer"

    parsed = parse_query(query)

    job = make_job(
        title="Applications Developer",
        skills=["react"],
    )

    ranked = rerank_jobs(
        [job],
        parsed,
    )

    assert ranked, (
        "Expected at least one ranked job"
    )

    ranked[0]["match_quality"] = (
        classify_match(
            ranked[0],
            parsed,
        )
    )

    report = summarize_search(
        query,
        ranked,
    )

    assert report["total_results"] == 1

    assert report["best_job"] is not None

    print("PASS: explanation layer")


def assert_wrong_location_rejected() -> None:
    query = "software engineer remote"

    plan = plan_query(query)

    job = make_job(
        title="Software Engineer",
        location="Bangalore",
    )

    keep, reason = candidate_passes_plan(
        job,
        plan,
    )

    assert not keep, (
        "A known non-remote location "
        "must not pass a remote search"
    )

    print("PASS: wrong location rejected")


def assert_wrong_experience_rejected() -> None:
    query = "entry level software engineer"

    plan = plan_query(query)

    job = make_job(
        title="Software Engineer",
        experience="8+ years of experience",
    )

    keep, reason = candidate_passes_plan(
        job,
        plan,
    )

    assert not keep, (
        "A senior experience requirement "
        "must not pass an entry-level query"
    )

    print("PASS: wrong experience rejected")


def assert_senior_query() -> None:
    query = "senior Python backend engineer"

    plan = plan_query(query)

    senior_job = make_job(
        title="Senior Backend Engineer",
        skills=["python"],
        experience="7+ years of experience",
    )

    junior_job = make_job(
        title="Junior Backend Engineer",
        skills=["python"],
        experience="1 year of experience",
    )

    keep_senior, _ = candidate_passes_plan(
        senior_job,
        plan,
    )

    keep_junior, _ = candidate_passes_plan(
        junior_job,
        plan,
    )

    assert keep_senior, (
        "A genuine senior backend engineer "
        "should pass"
    )

    assert not keep_junior, (
        "A junior backend engineer "
        "should not pass a senior query"
    )

    print("PASS: senior query")


def assert_full_skill_coverage() -> None:
    query = "React Node.js full stack developer"

    parsed = parse_query(query)

    strong_job = make_job(
        title="Full Stack Developer",
        skills=["React", "Node.js"],
    )

    partial_job = make_job(
        title="Full Stack Developer",
        skills=["React"],
    )

    strong_ranked = rerank_jobs(
        [strong_job],
        parsed,
    )

    partial_ranked = rerank_jobs(
        [partial_job],
        parsed,
    )

    assert strong_ranked
    assert partial_ranked

    strong_quality = classify_match(
        strong_ranked[0],
        parsed,
    )

    partial_quality = classify_match(
        partial_ranked[0],
        parsed,
    )

    assert strong_quality == "strong", (
        f"Expected strong, got {strong_quality}"
    )

    assert partial_quality == "partial", (
        f"Expected partial, got {partial_quality}"
    )

    print("PASS: skill coverage")


def assert_case_insensitive_skills() -> None:
    query = "React Node.js full stack developer"

    plan = plan_query(query)

    job = make_job(
        title="Full Stack Developer",
        skills=["REACT", "NODEJS"],
    )

    keep, reason = candidate_passes_plan(
        job,
        plan,
    )

    assert keep, (
        "Skill aliases should be "
        "matched case-insensitively"
    )

    print("PASS: skill aliases")


def assert_role_only_mismatch() -> None:
    query = "software engineer"

    plan = plan_query(query)

    job = make_job(
        title="Marketing Manager",
    )

    keep, reason = candidate_passes_plan(
        job,
        plan,
    )

    assert not keep, (
        "An unrelated role must not pass "
        "a role-only query"
    )

    print("PASS: role mismatch")


def assert_missing_location_allowed() -> None:
    query = "software engineer remote"

    plan = plan_query(query)

    job = make_job(
        title="Software Engineer",
        location="",
    )

    keep, reason = candidate_passes_plan(
        job,
        plan,
    )

    assert keep, (
        "A job with missing location data "
        "should remain eligible"
    )

    print("PASS: missing location allowed")


def assert_missing_experience_allowed() -> None:
    query = "entry level software engineer"

    plan = plan_query(query)

    job = make_job(
        title="Software Engineer",
        experience="",
    )

    keep, reason = candidate_passes_plan(
        job,
        plan,
    )

    assert keep, (
        "A job with missing experience data "
        "should remain eligible"
    )

    print("PASS: missing experience allowed")


def main() -> None:
    print("=" * 70)
    print("LOCAL RANKING TEST SUITE")
    print("=" * 70)

    assert_parser()
    assert_role_and_skill_gating()
    assert_partial_skill_match()
    assert_strong_match()
    assert_entry_level()
    assert_remote_constraint()
    assert_explanation()
    assert_wrong_location_rejected()
    assert_wrong_experience_rejected()
    assert_senior_query()
    assert_full_skill_coverage()
    assert_case_insensitive_skills()
    assert_role_only_mismatch()
    assert_missing_location_allowed()
    assert_missing_experience_allowed()

    print()
    print("=" * 70)
    print("ALL LOCAL TESTS PASSED")
    print("=" * 70)


if __name__ == "__main__":
    main()