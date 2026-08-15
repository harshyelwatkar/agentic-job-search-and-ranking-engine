from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from ranking.query_parser import ParsedQuery, parse_query


@dataclass
class SearchPlan:
    """
    Structured representation of the user's job-search intent.

    Phase 12 turns the parsed query into an explicit execution
    plan. The plan now controls both retrieval strategy and
    candidate-filtering strictness.
    """

    raw_query: str
    role_terms: list[str]
    skills: list[str]
    locations: list[str]
    experience_years: int | None
    entry_level: bool
    senior_level: bool
    employment_types: list[str]

    # Retrieval decision.
    retrieval_mode: str

    # Matching requirements.
    requires_skill_matching: bool
    requires_location_matching: bool
    requires_experience_matching: bool

    # Candidate-gating policy.
    gate_mode: str
    minimum_skill_coverage: float
    require_location_match: bool
    require_experience_match: bool


def build_search_plan(
    parsed: ParsedQuery,
) -> SearchPlan:
    """
    Convert ParsedQuery into an explicit search plan.

    The planner determines:

    1. Which Vespa retrieval profile to use.
    2. How strict the downstream candidate gate should be.
    """

    has_role = bool(
        parsed.role_terms
    )

    has_skills = bool(
        parsed.skills
    )

    has_location = bool(
        parsed.locations
    )

    has_experience = (
        parsed.experience_years is not None
        or parsed.entry_level
        or parsed.senior_level
    )

    # --------------------------------------------------------
    # Capability flags
    # --------------------------------------------------------

    requires_skill_matching = has_skills

    requires_location_matching = has_location

    requires_experience_matching = has_experience

    # --------------------------------------------------------
    # Retrieval strategy
    # --------------------------------------------------------

    if has_role and has_skills:
        retrieval_mode = "hybrid"

    elif has_skills and not has_role:
        retrieval_mode = "semantic"

    elif has_role and not has_skills:
        retrieval_mode = "bm25"

    else:
        retrieval_mode = "hybrid"

    # --------------------------------------------------------
    # Candidate-gating policy
    #
    # Highly constrained queries become stricter.
    # --------------------------------------------------------

    constraint_count = sum(
        [
            has_role,
            has_skills,
            has_location,
            has_experience,
        ]
    )

    if (
        has_role
        and has_skills
        and has_location
        and has_experience
    ):
        # Example:
        # senior Python backend AWS engineer remote
        gate_mode = "strict"

        minimum_skill_coverage = 0.50

        require_location_match = True
        require_experience_match = True

    elif constraint_count >= 3:
        gate_mode = "strict"

        minimum_skill_coverage = (
            0.50
            if has_skills
            else 0.0
        )

        require_location_match = has_location
        require_experience_match = has_experience

    elif constraint_count == 2:
        gate_mode = "normal"

        minimum_skill_coverage = (
            0.50
            if has_skills
            else 0.0
        )

        require_location_match = has_location
        require_experience_match = has_experience

    else:
        gate_mode = "soft"

        minimum_skill_coverage = (
            0.50
            if has_skills
            else 0.0
        )

        require_location_match = False
        require_experience_match = False

    return SearchPlan(
        raw_query=parsed.raw_query,
        role_terms=list(
            parsed.role_terms
        ),
        skills=list(
            parsed.skills
        ),
        locations=list(
            parsed.locations
        ),
        experience_years=(
            parsed.experience_years
        ),
        entry_level=parsed.entry_level,
        senior_level=parsed.senior_level,
        employment_types=list(
            parsed.employment_types
        ),
        retrieval_mode=retrieval_mode,
        requires_skill_matching=(
            requires_skill_matching
        ),
        requires_location_matching=(
            requires_location_matching
        ),
        requires_experience_matching=(
            requires_experience_matching
        ),
        gate_mode=gate_mode,
        minimum_skill_coverage=(
            minimum_skill_coverage
        ),
        require_location_match=(
            require_location_match
        ),
        require_experience_match=(
            require_experience_match
        ),
    )


def plan_query(
    query: str,
) -> SearchPlan:
    cleaned_query = query.strip()

    if not cleaned_query:
        raise ValueError(
            "Search query cannot be empty."
        )

    parsed = parse_query(
        cleaned_query
    )

    return build_search_plan(
        parsed
    )


def plan_to_dict(
    plan: SearchPlan,
) -> dict[str, Any]:
    return asdict(plan)


def print_search_plan(
    plan: SearchPlan,
) -> None:

    print()
    print("=" * 75)
    print("PHASE 12 QUERY PLAN")
    print("=" * 75)

    print(
        "Raw query:",
        plan.raw_query,
    )

    print(
        "Role terms:",
        plan.role_terms or "none",
    )

    print(
        "Skills:",
        plan.skills or "none",
    )

    print(
        "Locations:",
        plan.locations or "none",
    )

    print(
        "Experience years:",
        (
            plan.experience_years
            if plan.experience_years is not None
            else "none"
        ),
    )

    print(
        "Entry level:",
        plan.entry_level,
    )

    print(
        "Senior level:",
        plan.senior_level,
    )

    print(
        "Employment:",
        plan.employment_types or "none",
    )

    print(
        "Retrieval mode:",
        plan.retrieval_mode,
    )

    print(
        "Requires skill matching:",
        plan.requires_skill_matching,
    )

    print(
        "Requires location matching:",
        plan.requires_location_matching,
    )

    print(
        "Requires experience matching:",
        plan.requires_experience_matching,
    )

    print(
        "Gate mode:",
        plan.gate_mode,
    )

    print(
        "Minimum skill coverage:",
        plan.minimum_skill_coverage,
    )

    print(
        "Require location match:",
        plan.require_location_match,
    )

    print(
        "Require experience match:",
        plan.require_experience_match,
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


if __name__ == "__main__":
    main()