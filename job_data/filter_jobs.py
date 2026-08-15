from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


BASE_DIR = Path(__file__).resolve().parent

INPUT_FILE = BASE_DIR / "jobs.jsonl"
OUTPUT_FILE = BASE_DIR / "jobs_clean.jsonl"


# ============================================================
# Strong positive signals
# ============================================================

JOB_TITLE_TERMS = [
    "engineer",
    "developer",
    "software",
    "developer",
    "architect",
    "analyst",
    "scientist",
    "manager",
    "director",
    "administrator",
    "consultant",
    "designer",
    "researcher",
    "professor",
    "lecturer",
    "instructor",
    "specialist",
    "advisor",
    "associate",
    "technician",
    "operator",
    "coordinator",
    "accountant",
    "recruiter",
    "intern",
    "trainee",
    "apprentice",
    "administrator",
    "support",
    "sales",
    "marketing",
    "nurse",
    "doctor",
    "therapist",
    "counselor",
    "counsellor",
    "attorney",
    "lawyer",
    "mechanic",
    "electrician",
    "scientist",
    "professor",
]


JOB_LANGUAGE_TERMS = [
    "job description",
    "job details",
    "job title",
    "job type",
    "job role",
    "job posting",
    "job opening",
    "position",
    "responsibilities",
    "qualifications",
    "requirements",
    "required skills",
    "experience required",
    "years of experience",
    "how to apply",
    "apply now",
    "apply today",
    "employment type",
    "salary",
    "salary range",
    "benefits",
    "we are hiring",
    "we're hiring",
    "currently hiring",
    "currently looking for",
    "career opportunity",
    "open position",
    "vacancy",
    "full-time",
    "part-time",
    "internship",
    "contract",
]


JOB_URL_TERMS = [
    "/job/",
    "/jobs/",
    "/career/",
    "/careers/",
    "/job-opening/",
    "/job-openings/",
    "/position/",
    "/positions/",
    "/employment/",
    "/vacancy/",
    "/vacancies/",
]


# ============================================================
# Strong negative signals
# ============================================================

NON_JOB_TITLE_TERMS = [
    "5 ways",
    "10 ways",
    "how to",
    "what is",
    "why you should",
    "tips",
    "guide",
    "tutorial",
    "review",
    "reviews",
    "recipe",
    "recipes",
    "news",
    "blog",
    "article",
    "opinion",
    "podcast",
    "video",
    "webinar",
    "case study",
    "whitepaper",
    "press release",
    "forecast",
    "analysis",
]


NON_JOB_URL_TERMS = [
    "/blog/",
    "/blogs/",
    "/news/",
    "/article/",
    "/articles/",
    "/posts/",
    "/post/",
    "/guides/",
    "/guide/",
    "/recipes/",
    "/recipe/",
    "/podcast/",
    "/videos/",
    "/video/",
    "/webinar/",
    "/whitepaper/",
    "/press/",
]


# ============================================================
# Helpers
# ============================================================

def normalize(value: Any) -> str:
    if value is None:
        return ""

    return re.sub(
        r"\s+",
        " ",
        str(value).lower(),
    ).strip()


def contains_any(
    text: str,
    terms: list[str],
) -> bool:
    return any(
        term in text
        for term in terms
    )


def count_matches(
    text: str,
    terms: list[str],
) -> int:
    return sum(
        1
        for term in terms
        if term in text
    )


# ============================================================
# Job quality scoring
# ============================================================

def classify_job(
    record: dict[str, Any],
) -> tuple[bool, int, list[str]]:

    title = normalize(record.get("title"))
    company = normalize(record.get("company"))
    description = normalize(record.get("description"))
    url = normalize(record.get("url"))
    location = normalize(record.get("location"))
    experience = normalize(record.get("experience"))
    employment_type = normalize(record.get("employment_type"))
    salary = normalize(record.get("salary"))

    skills = record.get("skills") or []

    if isinstance(skills, list):
        skills_text = " ".join(
            normalize(skill)
            for skill in skills
        )
    else:
        skills_text = normalize(skills)

    score = 0
    reasons: list[str] = []

    title_matches = count_matches(
        title,
        JOB_TITLE_TERMS,
    )

    job_language_matches = count_matches(
        description,
        JOB_LANGUAGE_TERMS,
    )

    has_job_url = contains_any(
        url,
        JOB_URL_TERMS,
    )

    has_structured_metadata = any(
        [
            company,
            location,
            experience,
            employment_type,
            salary,
            skills_text,
        ]
    )

    # --------------------------------------------------------
    # Strong positive signals
    # --------------------------------------------------------

    if title_matches >= 1:
        score += 3
        reasons.append(
            f"title_terms={title_matches}"
        )

    if has_job_url:
        score += 3
        reasons.append("job_url")

    if job_language_matches >= 2:
        score += 3
        reasons.append(
            f"job_language={job_language_matches}"
        )
    elif job_language_matches == 1:
        score += 1
        reasons.append("job_language=1")

    if company:
        score += 1
        reasons.append("company")

    if location:
        score += 1
        reasons.append("location")

    if experience:
        score += 1
        reasons.append("experience")

    if employment_type:
        score += 1
        reasons.append("employment_type")

    if salary:
        score += 1
        reasons.append("salary")

    if skills_text:
        score += 1
        reasons.append("skills")

    # --------------------------------------------------------
    # Strong title structure
    # --------------------------------------------------------

    has_real_job_title = bool(
        re.search(
            r"\b("
            r"engineer|developer|architect|analyst|"
            r"scientist|manager|director|designer|"
            r"specialist|advisor|associate|consultant|"
            r"administrator|coordinator|technician|"
            r"professor|lecturer|instructor|researcher|"
            r"intern|trainee|apprentice|"
            r"accountant|recruiter|"
            r"nurse|doctor|therapist|counselor|"
            r"counsellor|attorney|lawyer|"
            r"mechanic|electrician|operator|"
            r"support|sales|marketing"
            r")\b",
            title,
            re.IGNORECASE,
        )
    )

    if has_real_job_title:
        score += 2
        reasons.append("job_title_structure")

    # --------------------------------------------------------
    # Strong negative signals
    # --------------------------------------------------------

    negative_title_matches = count_matches(
        title,
        NON_JOB_TITLE_TERMS,
    )

    if negative_title_matches:
        score -= 6
        reasons.append(
            f"negative_title={negative_title_matches}"
        )

    if contains_any(
        url,
        NON_JOB_URL_TERMS,
    ):
        score -= 7
        reasons.append("non_job_url")

    if title.startswith(
        (
            "5 ways",
            "10 ways",
            "how to",
            "what is",
            "why ",
            "craft ",
            "3 reasons",
        )
    ):
        score -= 7
        reasons.append("article_like_title")

    if len(title) > 180:
        score -= 3
        reasons.append("title_too_long")

    if title and len(title) < 5:
        score -= 4
        reasons.append("title_too_short")

    # --------------------------------------------------------
    # Explicit acceptance rules
    # --------------------------------------------------------

    # Rule A:
    # Strong job title + job URL.
    strong_rule_a = (
        has_real_job_title
        and has_job_url
    )

    # Rule B:
    # Strong structured job metadata + job URL.
    strong_rule_b = (
        has_job_url
        and has_structured_metadata
        and job_language_matches >= 1
    )

    # Rule C:
    # Strong job language + credible title,
    # even when URL structure is unusual.
    strong_rule_c = (
        has_real_job_title
        and job_language_matches >= 2
    )

    accepted = (
        score >= 7
        and (
            strong_rule_a
            or strong_rule_b
            or strong_rule_c
        )
    )

    reasons.append(
        "ACCEPT"
        if accepted
        else "REJECT"
    )

    return (
        accepted,
        score,
        reasons,
    )

# ============================================================
# Main
# ============================================================

def main() -> None:

    if not INPUT_FILE.exists():
        raise FileNotFoundError(
            f"Input file not found: {INPUT_FILE}"
        )

    total = 0
    accepted = 0
    rejected = 0

    accepted_records: list[
        dict[str, Any]
    ] = []

    rejected_examples: list[
        dict[str, Any]
    ] = []

    with INPUT_FILE.open(
        "r",
        encoding="utf-8",
    ) as input_file:

        for line in input_file:

            line = line.strip()

            if not line:
                continue

            record = json.loads(line)

            total += 1

            is_job, score, reasons = classify_job(
                record
            )

            record["filter_score"] = score
            record["filter_reasons"] = reasons

            if is_job:
                accepted += 1
                accepted_records.append(
                    record
                )
            else:
                rejected += 1

                if len(rejected_examples) < 15:
                    rejected_examples.append(
                        record
                    )

    # Highest-confidence records first.
    accepted_records.sort(
        key=lambda item: (
            item.get("filter_score", 0),
            item.get("heuristic_score", 0),
        ),
        reverse=True,
    )

    with OUTPUT_FILE.open(
        "w",
        encoding="utf-8",
    ) as output_file:

        for record in accepted_records:

            output_file.write(
                json.dumps(
                    record,
                    ensure_ascii=False,
                )
                + "\n"
            )

    # ========================================================
    # Summary
    # ========================================================

    print("=" * 65)
    print("JOB CORPUS FILTERING COMPLETE")
    print("=" * 65)

    print(
        f"Input records:      {total}"
    )

    print(
        f"Accepted job pages: {accepted}"
    )

    print(
        f"Rejected pages:     {rejected}"
    )

    print(
        f"Output file:        {OUTPUT_FILE}"
    )

    if total:
        percentage = (
            accepted / total
        ) * 100

        print(
            f"Acceptance rate:    {percentage:.1f}%"
        )

    print()
    print("=" * 65)
    print("ACCEPTED EXAMPLES")
    print("=" * 65)

    for index, record in enumerate(
        accepted_records[:10],
        start=1,
    ):
        print()
        print(
            f"{index}. "
            f"{record.get('title')}"
        )

        print(
            f"   Company: "
            f"{record.get('company') or 'N/A'}"
        )

        print(
            f"   Score: "
            f"{record.get('filter_score')}"
        )

        print(
            f"   URL: "
            f"{record.get('url')}"
        )

    print()
    print("=" * 65)
    print("REJECTED EXAMPLES")
    print("=" * 65)

    for index, record in enumerate(
        rejected_examples[:10],
        start=1,
    ):
        print()
        print(
            f"{index}. "
            f"{record.get('title')}"
        )

        print(
            f"   Score: "
            f"{record.get('filter_score')}"
        )

        print(
            f"   Reasons: "
            f"{', '.join(record.get('filter_reasons', []))}"
        )

        print(
            f"   URL: "
            f"{record.get('url')}"
        )


if __name__ == "__main__":
    main()