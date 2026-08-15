from __future__ import annotations

from typing import Any

from agent import SearchPlan
from ranking.job_ranker import calculate_features


def _parsed_query_from_plan(
    plan: SearchPlan,
):
    from ranking.query_parser import ParsedQuery

    return ParsedQuery(
        raw_query=plan.raw_query,
        role_terms=list(plan.role_terms),
        skills=list(plan.skills),
        locations=list(plan.locations),
        experience_years=plan.experience_years,
        employment_types=list(plan.employment_types),
        entry_level=plan.entry_level,
        senior_level=plan.senior_level,
    )


def candidate_passes_plan(
    job: dict[str, Any],
    plan: SearchPlan,
) -> tuple[bool, str]:

    parsed = _parsed_query_from_plan(
        plan
    )

    features = calculate_features(
        job,
        parsed,
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

    location_score = float(
        features.get(
            "location",
            0.0,
        )
    )

    experience_score = float(
        features.get(
            "experience",
            0.0,
        )
    )

    has_explicit_location = bool(
        str(
            job.get("location") or ""
        ).strip()
    )

    has_explicit_experience = bool(
        str(
            job.get("experience") or ""
        ).strip()
    )

    role_match = (
        role_score >= 0.30
    )

    skill_match = (
        skill_score
        >= plan.minimum_skill_coverage
    )

    # Reject explicit conflicts first.
    if (
        plan.require_location_match
        and has_explicit_location
        and location_score < 1.0
    ):
        return (
            False,
            "explicit_location_mismatch",
        )

    if (
        plan.require_experience_match
        and has_explicit_experience
        and experience_score <= 0.0
    ):
        return (
            False,
            "explicit_experience_mismatch",
        )

    # Strict mode.
    if plan.gate_mode == "strict":

        if (
            plan.role_terms
            and role_score < 0.50
        ):
            return (
                False,
                "strict_role_mismatch",
            )

        if (
            plan.requires_skill_matching
            and skill_score
            < plan.minimum_skill_coverage
        ):
            return (
                False,
                "strict_skill_mismatch",
            )

        reasons: list[str] = [
            f"role={role_score:.2f}"
        ]

        if plan.requires_skill_matching:
            reasons.append(
                f"skills={skill_score:.2f}"
            )

        if plan.require_location_match:
            reasons.append(
                "location_"
                + (
                    "verified"
                    if has_explicit_location
                    else "unknown"
                )
            )

        if plan.require_experience_match:
            reasons.append(
                "experience_"
                + (
                    "verified"
                    if has_explicit_experience
                    else "unknown"
                )
            )

        return (
            True,
            "; ".join(reasons),
        )

    # Normal mode.
    if plan.gate_mode == "normal":

        if (
            plan.role_terms
            and plan.requires_skill_matching
        ):
            if not role_match:
                return (
                    False,
                    "role_mismatch",
                )

            if not skill_match:
                return (
                    False,
                    "insufficient_skill_coverage",
                )

            return (
                True,
                f"role={role_score:.2f};"
                f"skills={skill_score:.2f}",
            )

        if plan.role_terms:
            if role_match:
                return (
                    True,
                    f"role={role_score:.2f}",
                )

            return (
                False,
                "role_mismatch",
            )

        if plan.requires_skill_matching:
            if skill_match:
                return (
                    True,
                    f"skills={skill_score:.2f}",
                )

            return (
                False,
                "insufficient_skill_coverage",
            )

        return (
            False,
            "no_role_or_skill_match",
        )

    # Soft mode.
    if plan.gate_mode == "soft":

        if role_score > 0.0:
            return (
                True,
                f"soft_role={role_score:.2f}",
            )

        if skill_score > 0.0:
            return (
                True,
                f"soft_skill={skill_score:.2f}",
            )

        return (
            False,
            "no_structured_match",
        )

    return (
        False,
        "unknown_gate_mode",
    )