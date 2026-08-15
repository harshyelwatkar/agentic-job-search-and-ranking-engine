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

    parsed = _parsed_query_from_plan(plan)

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

    matched_skills = features.get(
        "matched_skills",
        [],
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

    # ========================================================
    # STRICT MODE
    # ========================================================

    if plan.gate_mode == "strict":

        # ----------------------------------------------------
        # Role requirement
        # ----------------------------------------------------

        if plan.role_terms:

            if role_score < 0.50:
                return (
                    False,
                    "strict_role_mismatch",
                )

        # ----------------------------------------------------
        # Skill requirement
        # ----------------------------------------------------

        if plan.requires_skill_matching:

            if (
                skill_score
                < plan.minimum_skill_coverage
            ):
                return (
                    False,
                    "strict_skill_mismatch",
                )

        # ----------------------------------------------------
        # Location requirement
        #
        # Missing location = unknown.
        # Explicit conflicting location = reject.
        # ----------------------------------------------------

        if plan.require_location_match:

            if has_explicit_location:

                if location_score < 1.0:
                    return (
                        False,
                        "explicit_location_mismatch",
                    )

        # ----------------------------------------------------
        # Experience requirement
        #
        # Missing experience = unknown.
        # Explicit conflicting experience = reject.
        # ----------------------------------------------------

        if plan.require_experience_match:

            if has_explicit_experience:

                if experience_score <= 0.0:
                    return (
                        False,
                        "explicit_experience_mismatch",
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

    # ========================================================
    # NORMAL MODE
    # ========================================================

    if plan.gate_mode == "normal":

        role_match = (
            role_score >= 0.30
        )

        skill_match = (
            skill_score
            >= plan.minimum_skill_coverage
        )

        # ----------------------------------------------------
        # Role + explicit skills
        #
        # For a normal query containing both a role and
        # explicit skills, require evidence from both.
        #
        # We intentionally do NOT allow a skill-only match
        # to pass here. That prevents cases such as:
        #
        # "Java Spring Boot developer"
        #     -> Electrical Systems Engineer
        #        with only "java"
        #
        # from being treated as eligible.
        # ----------------------------------------------------

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

        # ----------------------------------------------------
        # Role-only query
        # ----------------------------------------------------

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

        # ----------------------------------------------------
        # Skill-only query
        # ----------------------------------------------------

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
    
    # ========================================================
    # SOFT MODE
    # ========================================================

    if plan.gate_mode == "soft":

        if role_score > 0.0:

            return (
                True,
                f"soft_role={role_score:.2f}",
            )

        if matched_skills:

            return (
                True,
                "soft_skill_match="
                + ",".join(
                    matched_skills
                ),
            )

        return (
            False,
            "no_structured_match",
        )

    # ========================================================
    # UNKNOWN MODE
    # ========================================================

    return (
        False,
        "unknown_gate_mode",
    )