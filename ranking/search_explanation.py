from __future__ import annotations

from typing import Any


def _quality_label(
    job: dict[str, Any],
) -> str:
    return str(
        job.get(
            "match_quality",
            "unknown",
        )
    )


def _format_skills(
    skills: list[str],
) -> str:
    if not skills:
        return "none"

    return ", ".join(skills)


def explain_job_match(
    job: dict[str, Any],
) -> dict[str, Any]:

    features = job.get(
        "ranking_features",
        {},
    )

    matched_skills = list(
        features.get(
            "matched_skills",
            [],
        )
    )

    missing_skills = list(
        features.get(
            "missing_skills",
            [],
        )
    )

    role_score = float(
        features.get(
            "title",
            0.0,
        )
    )

    skill_score = float(
        features.get(
            "skills",
            0.0,
        )
    )

    experience_score = float(
        features.get(
            "experience",
            0.0,
        )
    )

    location_score = float(
        features.get(
            "location",
            0.0,
        )
    )

    employment_score = float(
        features.get(
            "employment",
            0.0,
        )
    )

    quality = _quality_label(
        job
    )

    reasons: list[str] = []

    # --------------------------------------------------------
    # Skill explanation
    # --------------------------------------------------------

    if matched_skills:
        reasons.append(
            "Matched skills: "
            + _format_skills(
                matched_skills
            )
        )

    if missing_skills:
        reasons.append(
            "Missing skills: "
            + _format_skills(
                missing_skills
            )
        )

    # --------------------------------------------------------
    # Role explanation
    # --------------------------------------------------------

    if role_score >= 0.85:
        reasons.append(
            "Strong role compatibility"
        )
    elif role_score >= 0.30:
        reasons.append(
            "Related role, but not an exact "
            "role match"
        )
    else:
        reasons.append(
            "Role does not closely match "
            "the requested position"
        )

    # --------------------------------------------------------
    # Experience
    # --------------------------------------------------------

    if experience_score >= 1.0:
        reasons.append(
            "Experience level is compatible"
        )

    # --------------------------------------------------------
    # Location
    # --------------------------------------------------------

    if location_score >= 1.0:
        reasons.append(
            "Location requirement is satisfied"
        )

    # --------------------------------------------------------
    # Employment
    # --------------------------------------------------------

    if employment_score >= 1.0:
        reasons.append(
            "Employment type is compatible"
        )

    return {
        "quality": quality,
        "reasons": reasons,
        "matched_skills": matched_skills,
        "missing_skills": missing_skills,
        "role_score": role_score,
        "skill_score": skill_score,
        "experience_score": experience_score,
        "location_score": location_score,
        "employment_score": employment_score,
    }


def summarize_search(
    query: str,
    results: list[dict[str, Any]],
) -> dict[str, Any]:

    strong = [
        job
        for job in results
        if _quality_label(job) == "strong"
    ]

    partial = [
        job
        for job in results
        if _quality_label(job) == "partial"
    ]

    weak = [
        job
        for job in results
        if _quality_label(job) == "weak"
    ]

    if strong:
        summary = (
            "Strong matches were found."
        )
    elif partial:
        summary = (
            "No strong match was found, "
            "but partial matches are available."
        )
    elif weak:
        summary = (
            "Only weak matches were found."
        )
    else:
        summary = (
            "No eligible jobs were found."
        )

    best_job = (
        results[0]
        if results
        else None
    )

    best_explanation = (
        explain_job_match(
            best_job
        )
        if best_job
        else None
    )

    return {
        "query": query,
        "summary": summary,
        "total_results": len(results),
        "strong_matches": len(strong),
        "partial_matches": len(partial),
        "weak_matches": len(weak),
        "best_job": (
            {
                "title": best_job.get(
                    "title"
                ),
                "company": best_job.get(
                    "company"
                ),
                "url": best_job.get(
                    "url"
                ),
                "quality": (
                    best_explanation.get(
                        "quality"
                    )
                    if best_explanation
                    else None
                ),
                "reasons": (
                    best_explanation.get(
                        "reasons"
                    )
                    if best_explanation
                    else []
                ),
            }
            if best_job
            else None
        ),
    }


def print_search_explanation(
    query: str,
    results: list[dict[str, Any]],
) -> None:

    report = summarize_search(
        query,
        results,
    )

    print()
    print("=" * 75)
    print("SEARCH EXPLANATION")
    print("=" * 75)

    print(
        "Summary:",
        report["summary"],
    )

    print(
        "Total results:",
        report["total_results"],
    )

    print(
        "Strong matches:",
        report["strong_matches"],
    )

    print(
        "Partial matches:",
        report["partial_matches"],
    )

    print(
        "Weak matches:",
        report["weak_matches"],
    )

    best_job = report[
        "best_job"
    ]

    if not best_job:
        return

    print()
    print(
        "Best available match:",
        best_job.get(
            "title"
        )
        or "Untitled",
    )

    print(
        "Company:",
        best_job.get(
            "company"
        )
        or "N/A",
    )

    print(
        "Match quality:",
        best_job.get(
            "quality"
        )
        or "unknown",
    )

    reasons = best_job.get(
        "reasons",
        [],
    )

    if reasons:
        print(
            "Why:"
        )

        for reason in reasons:
            print(
                f"  - {reason}"
            )


if __name__ == "__main__":
    main_text = (
        "This module is intended "
        "to be used by agent_search.py."
    )

    print(main_text)