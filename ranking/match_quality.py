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

    # --------------------------------------------------------
    # STRONG
    # --------------------------------------------------------

    if has_role and has_skills:

        if (
            role >= 0.85
            and skills >= 0.75
            and (
                not has_location
                or location >= 1.0
            )
        ):
            return "strong"

    if has_role and not has_skills:

        if (
            role >= 0.85
            and (
                not has_location
                or location >= 1.0
            )
        ):
            return "strong"

    # --------------------------------------------------------
    # PARTIAL
    # --------------------------------------------------------

    if has_skills:

        # At least one requested skill matched.
        if matched_skills:

            # A meaningful skill match with a compatible
            # role is partial.
            if (
                role >= 0.30
                or skills >= 0.50
            ):
                return "partial"

    if has_role:

        # Role-only partial match.
        if (
            role >= 0.30
            and not missing_skills
        ):
            return "partial"

    # --------------------------------------------------------
    # WEAK
    # --------------------------------------------------------

    return "weak"