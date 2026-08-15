from __future__ import annotations

from typing import Any

from ranking.query_parser import ParsedQuery


def classify_match(
    job: dict[str, Any],
    parsed: ParsedQuery,
) -> str:
    features = job.get(
        "ranking_features",
        {},
    )

    role = float(
        features.get("title", 0.0)
    )

    skills = float(
        features.get("skills", 0.0)
    )

    location = float(
        features.get("location", 0.0)
    )

    experience = float(
        features.get("experience", 0.0)
    )

    missing_skills = features.get(
        "missing_skills",
        [],
    )

    matched_skills = features.get(
        "matched_skills",
        [],
    )

    has_role = bool(
        parsed.role_terms
    )

    has_skills = bool(
        parsed.skills
    )

    has_location = bool(
        parsed.locations
    )

    has_experience_constraint = (
        parsed.experience_years is not None
        or parsed.entry_level
        or parsed.senior_level
    )

    location_ok = (
        not has_location
        or location >= 1.0
    )

    experience_ok = (
        not has_experience_constraint
        or experience >= 1.0
    )

    # Strong matches should satisfy the main constraints,
    # not just have a good title score.
    if has_role and has_skills:
        if (
            role >= 0.85
            and skills >= 0.75
            and location_ok
            and experience_ok
        ):
            return "strong"

    if has_role and not has_skills:
        if (
            role >= 0.85
            and location_ok
            and experience_ok
        ):
            return "strong"

    # Partial matches can satisfy some, but not all,
    # requested dimensions.
    if has_skills and matched_skills:
        if (
            role >= 0.30
            or skills >= 0.50
        ):
            return "partial"

    if has_role:
        if (
            role >= 0.30
            and not missing_skills
        ):
            return "partial"

    return "weak"
