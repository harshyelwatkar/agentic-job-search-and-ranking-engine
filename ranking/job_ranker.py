from __future__ import annotations

import re
from typing import Any

from ranking.query_parser import ParsedQuery


# ------------------------------------------------------------
# Main weighting
#
# Structured job fit is intentionally dominant.
# Retrieval is useful, but should not override a clear
# role or skill mismatch.
# ------------------------------------------------------------

RETRIEVAL_WEIGHT = 0.10
ROLE_WEIGHT = 0.30
SKILL_WEIGHT = 0.35
EXPERIENCE_WEIGHT = 0.10
LOCATION_WEIGHT = 0.10
EMPLOYMENT_WEIGHT = 0.05


SKILL_ALIASES: dict[str, set[str]] = {
    "node.js": {"node.js", "nodejs", "node"},
    "react": {"react", "react.js"},
    "next.js": {"next.js", "nextjs"},
}


def _normalize(value: Any) -> str:
    if value is None:
        return ""

    return re.sub(
        r"\s+",
        " ",
        str(value).lower(),
    ).strip()


def _job_text(
    job: dict[str, Any],
) -> str:
    parts = [
        job.get("title"),
        job.get("company"),
        job.get("description"),
        job.get("search_text"),
        job.get("location"),
        job.get("experience"),
        job.get("employment_type"),
        job.get("salary"),
    ]

    skills = job.get("skills") or []

    if isinstance(skills, list):
        parts.extend(skills)
    elif skills:
        parts.append(skills)

    return _normalize(
        " ".join(
            str(part)
            for part in parts
            if part
        )
    )


def _skills_from_job(
    job: dict[str, Any],
) -> set[str]:
    skills = job.get("skills") or []

    detected: set[str] = set()

    if isinstance(skills, list):
        for skill in skills:
            normalized = _normalize(skill)

            if normalized:
                detected.add(normalized)

    elif isinstance(skills, str):
        for skill in re.split(
            r"[,|;]",
            skills,
        ):
            normalized = _normalize(skill)

            if normalized:
                detected.add(normalized)

    return detected


def _skill_present_in_text(
    skill: str,
    text: str,
) -> bool:
    aliases = SKILL_ALIASES.get(
        skill,
        {skill},
    )

    for alias in aliases:
        if re.search(
            rf"(?<![a-z0-9])"
            rf"{re.escape(alias)}"
            rf"(?![a-z0-9])",
            text,
        ):
            return True

    return False


def _parse_experience_years(
    value: Any,
) -> int | None:
    text = _normalize(value)

    if not text:
        return None

    match = re.search(
        r"(\d+)\+?\s*(?:years?|yrs?)",
        text,
        re.IGNORECASE,
    )

    if match:
        return int(
            match.group(1)
        )

    return None


def _has_entry_level_signal(
    job: dict[str, Any],
) -> bool:
    text = _job_text(job)

    return bool(
        re.search(
            r"\b("
            r"entry[\s-]?level|"
            r"fresher(?:s)?|"
            r"new graduate|"
            r"graduate|"
            r"junior|"
            r"intern(?:ship)?|"
            r"trainee|"
            r"apprentice"
            r")\b",
            text,
            re.IGNORECASE,
        )
    )


def _has_senior_level_signal(
    job: dict[str, Any],
) -> bool:
    text = _job_text(job)

    return bool(
        re.search(
            r"\b("
            r"senior|"
            r"sr\.?|"
            r"lead|"
            r"principal|"
            r"staff"
            r")\b",
            text,
            re.IGNORECASE,
        )
    )


# ------------------------------------------------------------
# Role matching
# ------------------------------------------------------------

def role_match_score(
    job: dict[str, Any],
    parsed: ParsedQuery,
) -> float:
    title = _normalize(
        job.get("title")
    )

    if not title or not parsed.role_terms:
        return 0.0

    best_score = 0.0

    for role in parsed.role_terms:
        role_normalized = _normalize(role)

        # ----------------------------------------------------
        # Exact phrase match
        # ----------------------------------------------------
        if (
            role_normalized in title
            and len(
                role_normalized.split()
            ) >= 2
        ):
            best_score = max(
                best_score,
                1.0,
            )
            continue

        # ----------------------------------------------------
        # Full-stack developer
        # ----------------------------------------------------
        if role_normalized == (
            "full stack developer"
        ):
            if (
                "full stack" in title
                or "full-stack" in title
            ):
                best_score = max(
                    best_score,
                    1.0,
                )
            elif re.search(
                r"\bdeveloper\b",
                title,
                re.IGNORECASE,
            ):
                best_score = max(
                    best_score,
                    0.30,
                )
            continue

        # ----------------------------------------------------
        # Backend engineer
        # ----------------------------------------------------
        if role_normalized == (
            "backend engineer"
        ):
            if re.search(
                r"\bbackend\s+engineer\b",
                title,
                re.IGNORECASE,
            ):
                best_score = max(
                    best_score,
                    1.0,
                )
            elif re.search(
                r"\bback[-\s]?end\s+engineer\b",
                title,
                re.IGNORECASE,
            ):
                best_score = max(
                    best_score,
                    1.0,
                )
            elif (
                re.search(
                    r"\bbackend\b",
                    title,
                    re.IGNORECASE,
                )
                and re.search(
                    r"\bengineer\b",
                    title,
                    re.IGNORECASE,
                )
            ):
                best_score = max(
                    best_score,
                    0.85,
                )
            elif re.search(
                r"\bengineer\b",
                title,
                re.IGNORECASE,
            ):
                best_score = max(
                    best_score,
                    0.25,
                )
            continue

        # ----------------------------------------------------
        # Backend developer
        # ----------------------------------------------------
        if role_normalized == (
            "backend developer"
        ):
            if re.search(
                r"\bbackend\s+developer\b",
                title,
                re.IGNORECASE,
            ):
                best_score = max(
                    best_score,
                    1.0,
                )
            elif re.search(
                r"\bback[-\s]?end\s+developer\b",
                title,
                re.IGNORECASE,
            ):
                best_score = max(
                    best_score,
                    1.0,
                )
            elif re.search(
                r"\bdeveloper\b",
                title,
                re.IGNORECASE,
            ):
                best_score = max(
                    best_score,
                    0.30,
                )
            continue

        # ----------------------------------------------------
        # Java developer
        # ----------------------------------------------------
        if role_normalized == (
            "java developer"
        ):
            if re.search(
                r"\bjava\s+developer\b",
                title,
                re.IGNORECASE,
            ):
                best_score = max(
                    best_score,
                    1.0,
                )
            elif (
                re.search(
                    r"\bjava\b",
                    title,
                    re.IGNORECASE,
                )
                and re.search(
                    r"\bdeveloper\b",
                    title,
                    re.IGNORECASE,
                )
            ):
                best_score = max(
                    best_score,
                    0.90,
                )
            elif re.search(
                r"\bdeveloper\b",
                title,
                re.IGNORECASE,
            ):
                best_score = max(
                    best_score,
                    0.20,
                )
            continue

        # ----------------------------------------------------
        # Software engineer
        # ----------------------------------------------------
        if role_normalized == (
            "software engineer"
        ):
            if re.search(
                r"\bsoftware\s+engineer\b",
                title,
                re.IGNORECASE,
            ):
                best_score = max(
                    best_score,
                    1.0,
                )
            elif re.search(
                r"\bsoftware\s+developer\b",
                title,
                re.IGNORECASE,
            ):
                best_score = max(
                    best_score,
                    0.85,
                )
            elif (
                re.search(
                    r"\bengineer\b",
                    title,
                    re.IGNORECASE,
                )
                and re.search(
                    r"\bsoftware\b",
                    title,
                    re.IGNORECASE,
                )
            ):
                best_score = max(
                    best_score,
                    0.90,
                )
            elif re.search(
                r"\b(engineer|developer)\b",
                title,
                re.IGNORECASE,
            ):
                best_score = max(
                    best_score,
                    0.25,
                )
            continue

        # ----------------------------------------------------
        # Data engineer
        # ----------------------------------------------------
        if role_normalized == (
            "data engineer"
        ):
            if re.search(
                r"\bdata\s+engineer\b",
                title,
                re.IGNORECASE,
            ):
                best_score = max(
                    best_score,
                    1.0,
                )
            elif (
                re.search(
                    r"\bdata\b",
                    title,
                    re.IGNORECASE,
                )
                and re.search(
                    r"\bengineer\b",
                    title,
                    re.IGNORECASE,
                )
            ):
                best_score = max(
                    best_score,
                    0.80,
                )
            continue

        # ----------------------------------------------------
        # Machine learning engineer
        # ----------------------------------------------------
        if role_normalized == (
            "machine learning engineer"
        ):
            if re.search(
                r"\bmachine\s+learning\s+engineer\b",
                title,
                re.IGNORECASE,
            ):
                best_score = max(
                    best_score,
                    1.0,
                )
            elif re.search(
                r"\bmachine\s+learning\b",
                title,
                re.IGNORECASE,
            ):
                best_score = max(
                    best_score,
                    0.80,
                )
            elif re.search(
                r"\bengineer\b",
                title,
                re.IGNORECASE,
            ):
                best_score = max(
                    best_score,
                    0.25,
                )
            continue

        # ----------------------------------------------------
        # Generic engineer
        # ----------------------------------------------------
        if role_normalized == "engineer":
            if re.search(
                r"\bengineer(?:ing)?\b",
                title,
                re.IGNORECASE,
            ):
                best_score = max(
                    best_score,
                    0.60,
                )
            continue

        # ----------------------------------------------------
        # Generic developer
        # ----------------------------------------------------
        if role_normalized == "developer":
            if re.search(
                r"\bdeveloper\s+relations\b",
                title,
                re.IGNORECASE,
            ):
                continue

            if re.search(
                r"\bdeveloper\b",
                title,
                re.IGNORECASE,
            ):
                best_score = max(
                    best_score,
                    0.50,
                )

            continue

        # ----------------------------------------------------
        # Generic fallback
        # ----------------------------------------------------
        if role_normalized in title:
            best_score = max(
                best_score,
                0.50,
            )

    # --------------------------------------------------------
    # Experience-level intent
    # --------------------------------------------------------

    if parsed.entry_level:
        if _has_entry_level_signal(job):
            best_score = min(
                1.0,
                best_score + 0.15,
            )

        if _has_senior_level_signal(job):
            best_score *= 0.35

    if parsed.senior_level:
        if _has_senior_level_signal(job):
            best_score = min(
                1.0,
                best_score + 0.15,
            )

        if _has_entry_level_signal(job):
            best_score *= 0.40

    return round(
        best_score,
        6,
    )


# ------------------------------------------------------------
# Skill matching
# ------------------------------------------------------------

def skill_match_details(
    job: dict[str, Any],
    parsed: ParsedQuery,
) -> tuple[
    float,
    list[str],
    list[str],
]:
    requested = [
        _normalize(skill)
        for skill in parsed.skills
        if _normalize(skill)
    ]

    if not requested:
        return 0.0, [], []

    structured = _skills_from_job(job)
    full_text = _job_text(job)

    matched: list[str] = []
    missing: list[str] = []

    for skill in requested:
        if skill in structured:
            matched.append(skill)
            continue

        if _skill_present_in_text(
            skill,
            full_text,
        ):
            matched.append(skill)
        else:
            missing.append(skill)

    coverage = (
        len(matched) / len(requested)
        if requested
        else 0.0
    )

    return (
        coverage,
        matched,
        missing,
    )


# ------------------------------------------------------------
# Experience matching
# ------------------------------------------------------------

def experience_score(
    job: dict[str, Any],
    parsed: ParsedQuery,
) -> float:
    requested = parsed.experience_years

    if requested is not None:
        job_experience = (
            _parse_experience_years(
                job.get("experience")
            )
        )

        if job_experience is None:
            job_experience = (
                _parse_experience_years(
                    job.get("description")
                )
            )

        if job_experience is None:
            return 0.0

        if job_experience <= requested:
            return 1.0

        gap = (
            job_experience
            - requested
        )

        if gap == 1:
            return 0.75

        if gap == 2:
            return 0.50

        if gap == 3:
            return 0.25

        return 0.0

    if parsed.entry_level:
        if _has_entry_level_signal(job):
            return 1.0

        if _has_senior_level_signal(job):
            return 0.0

        return 0.35

    if parsed.senior_level:
        if _has_senior_level_signal(job):
            return 1.0

        if _has_entry_level_signal(job):
            return 0.0

        return 0.35

    return 0.0


# ------------------------------------------------------------
# Location matching
# ------------------------------------------------------------

def location_score(
    job: dict[str, Any],
    parsed: ParsedQuery,
) -> float:
    if not parsed.locations:
        return 0.0

    job_location = _normalize(
        job.get("location")
    )

    job_text = _job_text(job)

    for requested in parsed.locations:
        requested_normalized = _normalize(
            requested
        )

        if requested_normalized == "remote":
            if (
                "remote" in job_location
                or "remote" in job_text
            ):
                return 1.0

            continue

        if requested_normalized in job_location:
            return 1.0

        if requested_normalized in job_text:
            return 1.0

    return 0.0


# ------------------------------------------------------------
# Employment-type matching
# ------------------------------------------------------------

def employment_score(
    job: dict[str, Any],
    parsed: ParsedQuery,
) -> float:
    if not parsed.employment_types:
        return 0.0

    job_type = _normalize(
        job.get("employment_type")
    )

    job_text = _job_text(job)

    combined = (
        f"{job_type} {job_text}"
    )

    for requested in parsed.employment_types:
        if (
            _normalize(requested)
            in combined
        ):
            return 1.0

    return 0.0


# ------------------------------------------------------------
# Retrieval score
# ------------------------------------------------------------

def retrieval_score(
    job: dict[str, Any],
) -> float:
    raw = job.get(
        "relevance",
        0.0,
    )

    try:
        score = float(raw)
    except (
        TypeError,
        ValueError,
    ):
        return 0.0

    if score <= 0:
        return 0.0

    return score / (
        1.0 + score
    )


# ------------------------------------------------------------
# Feature calculation
# ------------------------------------------------------------

def calculate_features(
    job: dict[str, Any],
    parsed: ParsedQuery,
) -> dict[str, Any]:

    (
        skill_coverage,
        matched_skills,
        missing_skills,
    ) = skill_match_details(
        job,
        parsed,
    )

    return {
        "retrieval": retrieval_score(
            job
        ),
        "title": role_match_score(
            job,
            parsed,
        ),
        "skills": skill_coverage,
        "experience": experience_score(
            job,
            parsed,
        ),
        "location": location_score(
            job,
            parsed,
        ),
        "employment": employment_score(
            job,
            parsed,
        ),
        "matched_skills": matched_skills,
        "missing_skills": missing_skills,
    }


# ------------------------------------------------------------
# Final score
# ------------------------------------------------------------

def calculate_final_score(
    features: dict[str, Any],
) -> float:
    retrieval = features.get(
        "retrieval",
        0.0,
    )

    role = features.get(
        "title",
        0.0,
    )

    skills = features.get(
        "skills",
        0.0,
    )

    experience = features.get(
        "experience",
        0.0,
    )

    location = features.get(
        "location",
        0.0,
    )

    employment = features.get(
        "employment",
        0.0,
    )

    matched_skills = features.get(
        "matched_skills",
        [],
    )

    missing_skills = features.get(
        "missing_skills",
        [],
    )

    requested_skills_count = (
        len(matched_skills)
        + len(missing_skills)
    )

    score = (
        RETRIEVAL_WEIGHT * retrieval
        + ROLE_WEIGHT * role
        + SKILL_WEIGHT * skills
        + EXPERIENCE_WEIGHT * experience
        + LOCATION_WEIGHT * location
        + EMPLOYMENT_WEIGHT * employment
    )

    # Missing required-skill penalty.
    if requested_skills_count > 0:

        missing_ratio = (
            len(missing_skills)
            / requested_skills_count
        )

        score *= max(
            0.20,
            1.0 - 0.70 * missing_ratio,
        )

    # Explicit role mismatch penalty.
    role_requested = bool(
        features.get(
            "_role_requested",
            False,
        )
    )

    if role_requested and role <= 0.0:
        score *= 0.30

    return round(
        max(score, 0.0),
        6,
    )


# ------------------------------------------------------------
# Final ranking priority
#
# This is deliberately a secondary ordering signal.
# A meaningful partial skill match should outrank a weak
# role-only result when their numeric scores are close.
# ------------------------------------------------------------

def _match_quality_priority(
    job: dict[str, Any],
) -> int:
    features = job.get(
        "ranking_features",
        {},
    )

    matched_skills = features.get(
        "matched_skills",
        [],
    )

    missing_skills = features.get(
        "missing_skills",
        [],
    )

    role_score = float(
        features.get(
            "title",
            0.0,
        )
    )

    # Strong structured compatibility.
    if (
        role_score >= 0.85
        and matched_skills
        and not missing_skills
    ):
        return 3

    # Partial but meaningful skill match.
    if matched_skills:
        return 2

    # Meaningful role match without requested skills.
    if role_score >= 0.30:
        return 1

    return 0


# ------------------------------------------------------------
# Reranking
# ------------------------------------------------------------

def rerank_jobs(
    jobs: list[dict[str, Any]],
    parsed: ParsedQuery,
) -> list[dict[str, Any]]:

    reranked: list[
        dict[str, Any]
    ] = []

    for job in jobs:

        features = calculate_features(
            job,
            parsed,
        )

        features[
            "_role_requested"
        ] = bool(
            parsed.role_terms
        )

        enriched = dict(job)

        enriched[
            "ranking_features"
        ] = features

        enriched[
            "job_match_score"
        ] = calculate_final_score(
            features
        )

        reranked.append(
            enriched
        )

    reranked.sort(
        key=lambda item: (
            _match_quality_priority(
                item
            ),
            item.get(
                "job_match_score",
                0.0,
            ),
            item.get(
                "relevance",
                0.0,
            ),
        ),
        reverse=True,
    )

    return reranked