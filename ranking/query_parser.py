from __future__ import annotations

import re
from dataclasses import dataclass, field


@dataclass
class ParsedQuery:
    raw_query: str
    role_terms: list[str] = field(default_factory=list)
    skills: list[str] = field(default_factory=list)
    locations: list[str] = field(default_factory=list)
    experience_years: int | None = None
    employment_types: list[str] = field(default_factory=list)
    entry_level: bool = False
    senior_level: bool = False


SKILLS = {
    "python": "python",
    "java": "java",
    "javascript": "javascript",
    "typescript": "typescript",
    "react": "react",
    "react.js": "react",
    "node": "node.js",
    "node.js": "node.js",
    "nodejs": "node.js",
    "express": "express",
    "angular": "angular",
    "vue": "vue",
    "spring": "spring",
    "spring boot": "spring boot",
    "sql": "sql",
    "mysql": "mysql",
    "postgresql": "postgresql",
    "mongodb": "mongodb",
    "aws": "aws",
    "azure": "azure",
    "gcp": "gcp",
    "docker": "docker",
    "kubernetes": "kubernetes",
    "terraform": "terraform",
    "git": "git",
    "linux": "linux",
    "machine learning": "machine learning",
    "deep learning": "deep learning",
    "artificial intelligence": "artificial intelligence",
    "data science": "data science",
    "data engineering": "data engineering",
    "graphql": "graphql",
    "rest api": "rest api",
    "next.js": "next.js",
    "nextjs": "next.js",
    "html": "html",
    "css": "css",
    ".net": ".net",
    "c++": "c++",
    "c#": "c#",
    "excel": "excel",
}


ROLE_TERMS = {
    "software engineer",
    "software developer",
    "full stack developer",
    "full-stack developer",
    "frontend developer",
    "front end developer",
    "backend developer",
    "back end developer",
    "backend engineer",
    "back end engineer",
    "web developer",
    "mobile developer",
    "data engineer",
    "data scientist",
    "machine learning engineer",
    "ai engineer",
    "devops engineer",
    "cloud engineer",
    "qa engineer",
    "test engineer",
    "engineering manager",
    "product manager",
    "project manager",
    "business analyst",
    "system administrator",
    "administrator",
    "developer",
    "engineer",
    "analyst",
    "designer",
    "intern",
    "trainee",
}


LOCATION_HINTS = {
    "bangalore": "Bangalore",
    "bengaluru": "Bangalore",
    "hyderabad": "Hyderabad",
    "pune": "Pune",
    "mumbai": "Mumbai",
    "delhi": "Delhi",
    "new delhi": "Delhi",
    "gurgaon": "Gurgaon",
    "gurugram": "Gurgaon",
    "noida": "Noida",
    "chennai": "Chennai",
    "kolkata": "Kolkata",
    "ahmedabad": "Ahmedabad",
    "remote": "Remote",
    "usa": "USA",
    "united states": "USA",
    "uk": "UK",
    "united kingdom": "UK",
    "canada": "Canada",
}


def _unique_preserving_order(
    values: list[str],
) -> list[str]:
    seen: set[str] = set()
    output: list[str] = []

    for value in values:
        normalized = value.strip().lower()

        if not normalized or normalized in seen:
            continue

        seen.add(normalized)
        output.append(value.strip())

    return output


def _extract_experience(
    query: str,
) -> int | None:
    patterns = [
        r"\b(\d+)\+?\s*(?:years?|yrs?)\b",
        r"\b(?:at least|minimum of)\s+(\d+)\s*(?:years?|yrs?)\b",
    ]

    for pattern in patterns:
        match = re.search(
            pattern,
            query,
            re.IGNORECASE,
        )

        if match:
            return int(match.group(1))

    return None


def _extract_experience_intent(
    query: str,
) -> tuple[bool, bool]:
    normalized = query.lower()

    entry_level = bool(
        re.search(
            r"\b("
            r"entry[\s-]?level|"
            r"fresher(?:s)?|"
            r"graduate|"
            r"new graduate|"
            r"junior|"
            r"intern(?:ship)?|"
            r"trainee|"
            r"apprentice"
            r")\b",
            normalized,
        )
    )

    senior_level = bool(
        re.search(
            r"\b("
            r"senior|"
            r"sr\.?|"
            r"lead|"
            r"principal|"
            r"staff"
            r")\b",
            normalized,
        )
    )

    return entry_level, senior_level


def _extract_employment_types(
    query: str,
) -> list[str]:
    normalized = query.lower()

    detected: list[str] = []

    if re.search(
        r"\bfull[\s-]?time\b",
        normalized,
    ):
        detected.append("Full-Time")

    if re.search(
        r"\bpart[\s-]?time\b",
        normalized,
    ):
        detected.append("Part-Time")

    if re.search(
        r"\bintern(?:ship)?\b",
        normalized,
    ):
        detected.append("Internship")

    if re.search(
        r"\bcontract(?:or)?\b",
        normalized,
    ):
        detected.append("Contract")

    return detected


def _extract_skills(
    query: str,
) -> list[str]:
    normalized = query.lower()

    matches: list[str] = []

    for phrase, canonical in sorted(
        SKILLS.items(),
        key=lambda item: len(item[0]),
        reverse=True,
    ):
        if phrase in normalized:
            matches.append(canonical)

    matches = _unique_preserving_order(
        matches
    )

    # --------------------------------------------------------
    # Compound-skill normalization.
    #
    # "spring boot" already represents the Spring Boot skill,
    # so do not also treat "spring" as a separate requirement.
    # --------------------------------------------------------

    if "spring boot" in matches:
        matches = [
            skill
            for skill in matches
            if skill != "spring"
        ]

    return matches


def _extract_roles(
    query: str,
) -> list[str]:
    normalized = query.lower()

    matches: list[str] = []

    # --------------------------------------------------------
    # First detect explicit multi-word role phrases.
    # --------------------------------------------------------

    for role in sorted(
        ROLE_TERMS,
        key=len,
        reverse=True,
    ):
        if role in normalized:
            matches.append(role)

    matches = _unique_preserving_order(
        matches
    )

    # --------------------------------------------------------
    # Compose role intent from context.
    #
    # "python backend aws engineer"
    # -> "backend engineer"
    #
    # "java spring boot developer"
    # -> "software developer" / "developer"
    # with Java treated as the major specialization.
    # --------------------------------------------------------

    if (
        "backend" in normalized
        and "engineer" in normalized
        and "backend engineer" not in matches
    ):
        matches.insert(
            0,
            "backend engineer",
        )

    if (
        "back end" in normalized
        and "engineer" in normalized
    ):
        if "back end engineer" not in matches:
            matches.insert(
                0,
                "back end engineer",
            )

    if (
        "backend" in normalized
        and "developer" in normalized
        and "backend developer" not in matches
    ):
        matches.insert(
            0,
            "backend developer",
        )

    if (
        "back end" in normalized
        and "developer" in normalized
    ):
        if "back end developer" not in matches:
            matches.insert(
                0,
                "back end developer",
            )

    # --------------------------------------------------------
    # Java + developer strongly implies Java developer.
    # --------------------------------------------------------

    if (
        "java" in _extract_skills(query)
        and "developer" in normalized
    ):
        if "java developer" not in matches:
            matches.insert(
                0,
                "java developer",
            )

    # --------------------------------------------------------
    # Remove generic roles when a specific role exists.
    # --------------------------------------------------------

    specific_roles = [
        role
        for role in matches
        if role
        not in {
            "developer",
            "engineer",
            "analyst",
            "administrator",
        }
    ]

    if specific_roles:
        matches = [
            role
            for role in matches
            if role
            not in {
                "developer",
                "engineer",
                "analyst",
                "administrator",
            }
        ]

    return _unique_preserving_order(
        matches
    )


def _extract_locations(
    query: str,
) -> list[str]:
    normalized = query.lower()

    matches: list[str] = []

    for phrase, canonical in sorted(
        LOCATION_HINTS.items(),
        key=lambda item: len(item[0]),
        reverse=True,
    ):
        if phrase in normalized:
            matches.append(canonical)

    return _unique_preserving_order(
        matches
    )


def parse_query(
    query: str,
) -> ParsedQuery:
    cleaned = " ".join(
        query.strip().split()
    )

    (
        entry_level,
        senior_level,
    ) = _extract_experience_intent(
        cleaned
    )

    return ParsedQuery(
        raw_query=cleaned,
        role_terms=_extract_roles(
            cleaned
        ),
        skills=_extract_skills(
            cleaned
        ),
        locations=_extract_locations(
            cleaned
        ),
        experience_years=_extract_experience(
            cleaned
        ),
        employment_types=_extract_employment_types(
            cleaned
        ),
        entry_level=entry_level,
        senior_level=senior_level,
    )