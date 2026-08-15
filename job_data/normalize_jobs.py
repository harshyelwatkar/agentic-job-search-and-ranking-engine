from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlparse

BASE_DIR = Path(__file__).resolve().parent

INPUT_FILE = BASE_DIR / "candidate_jobs.jsonl"
OUTPUT_FILE = BASE_DIR / "jobs.jsonl"


# ============================================================
# Generic helpers
# ============================================================


def clean_text(value: Any) -> str:
    if value is None:
        return ""

    return re.sub(r"\s+", " ", str(value)).strip()


def clean_value(value: str) -> str:
    return re.sub(
        r"\s+",
        " ",
        value.replace("\r", " ").replace("\n", " "),
    ).strip(" :-–—|")


def first_match(
    patterns: list[str],
    text: str,
) -> str:
    for pattern in patterns:
        match = re.search(
            pattern,
            text,
            re.IGNORECASE | re.DOTALL,
        )

        if not match:
            continue

        value = clean_value(match.group(1))

        if value:
            return value

    return ""


def extract_domain(url: str) -> str:
    try:
        host = urlparse(url).hostname or ""
    except ValueError:
        return ""

    host = host.lower()

    if host.startswith("www."):
        host = host[4:]

    parts = host.split(".")

    if len(parts) >= 2:
        return parts[-2]

    return host


# ============================================================
# Title
# ============================================================


def extract_title(
    text: str,
    url: str,
) -> str:

    # --------------------------------------------------------
    # Explicit "Job Title:"
    # --------------------------------------------------------
    match = re.search(
        r"(?:^|\n)\s*Job Title\s*:\s*([^\n]+)",
        text,
        re.IGNORECASE,
    )

    if match:
        value = clean_value(match.group(1))

        if 8 <= len(value) <= 150:
            return value

    # --------------------------------------------------------
    # Explicit "Position Title:"
    # --------------------------------------------------------
    match = re.search(
        r"(?:^|\n)\s*Position Title\s*:\s*([^\n]+)",
        text,
        re.IGNORECASE,
    )

    if match:
        value = clean_value(match.group(1))

        if 8 <= len(value) <= 150:
            return value

    # --------------------------------------------------------
    # Common university/faculty format:
    #
    # "... seeks an outstanding faculty member for a
    # nine-month lecturer position in Psychology ..."
    # --------------------------------------------------------
    match = re.search(
        r"\b(?:lecturer|professor|faculty member|assistant professor|"
        r"associate professor|instructor)\s+position\s+in\s+"
        r"([A-Za-z][A-Za-z &/\-]+)",
        text,
        re.IGNORECASE,
    )

    if match:
        subject = clean_value(match.group(1))

        # Avoid accidentally consuming an entire sentence.
        subject = re.split(
            r"\b(?:beginning|starting|at|with|for)\b",
            subject,
            maxsplit=1,
            flags=re.IGNORECASE,
        )[0].strip()

        if subject:
            first_word = "Lecturer"

            return f"{first_word} " f"{subject}"

    # --------------------------------------------------------
    # "currently hiring ..."
    # --------------------------------------------------------
    patterns = [
        r"(?:currently hiring|currently looking for)\s+"
        r"(?:a|an|the)?\s*"
        r"([A-Z][A-Za-z0-9/&(),.'+\- ]{8,120}?)"
        r"\s+(?:to join|who will|for|position)",
        r"\b(?:seeks|seeking)\s+"
        r"(?:a|an|the)?\s*"
        r"([A-Z][A-Za-z0-9/&(),.'+\- ]{8,120}?)"
        r"\s+(?:for|to|position)",
    ]

    for pattern in patterns:
        match = re.search(
            pattern,
            text,
            re.IGNORECASE,
        )

        if match:
            value = clean_value(match.group(1))

            if 8 <= len(value) <= 150:
                return value

    # --------------------------------------------------------
    # Opening line + Job Description
    # --------------------------------------------------------
    match = re.search(
        r"^\s*(.{8,150}?)\s*Job Description\b",
        text,
        re.IGNORECASE,
    )

    if match:
        value = clean_value(match.group(1))

        if 8 <= len(value) <= 150:
            return value

    # --------------------------------------------------------
    # About this role
    # --------------------------------------------------------
    match = re.search(
        r"About this role:\s*([^\n:]{8,150})",
        text,
        re.IGNORECASE,
    )

    if match:
        value = clean_value(match.group(1))

        if 8 <= len(value) <= 150:
            return value

    # --------------------------------------------------------
    # URL fallback
    # --------------------------------------------------------
    try:
        path = urlparse(url).path
    except ValueError:
        path = ""

    segments = [unquote(x).strip() for x in path.split("/") if x.strip()]

    ignored = {
        "job",
        "jobs",
        "career",
        "careers",
        "position",
        "positions",
        "employment",
        "vacancy",
        "vacancies",
    }

    for segment in reversed(segments):

        lower = segment.lower()

        if lower in ignored:
            continue

        if re.fullmatch(
            r"\d{5,}",
            lower,
        ):
            continue

        if re.fullmatch(
            r"[a-f0-9]{16,}",
            lower,
        ):
            continue

        if lower.startswith("phn-phn-"):
            continue

        value = re.sub(
            r"[-_]+",
            " ",
            segment,
        )

        value = clean_value(value)

        if 8 <= len(value) <= 150:
            return value.title()

    return ""


# ============================================================
# Company
# ============================================================

KNOWN_DOMAINS = {
    "northropgrumman": "Northrop Grumman",
    "concentrix": "Concentrix",
    "wellsfargo": "Wells Fargo",
    "stripe": "Stripe",
    "hubinternational": "HUB International",
}


def extract_company(
    text: str,
    url: str,
) -> str:

    # --------------------------------------------------------
    # Explicit hiring organization
    # --------------------------------------------------------
    match = re.search(
        r"(?:^|\n)\s*Hiring Organization\s*[:\-]\s*([^\n]+)",
        text,
        re.IGNORECASE,
    )

    if match:
        value = clean_value(match.group(1))

        if 2 <= len(value) <= 100:
            return value

    # --------------------------------------------------------
    # University employer pattern
    # Example:
    # "University of North Carolina Wilmington (UNCW)"
    # --------------------------------------------------------
    match = re.search(
        r"\b((?:University|College|Institute|School)"
        r"(?:\s+of|\s+for)?"
        r"(?:\s+[A-Z][A-Za-z&.'\-]+){1,8})"
        r"\s*\(([A-Z]{2,8})\)",
        text,
    )

    if match:
        organization = clean_value(match.group(1))

        abbreviation = match.group(2)

        return f"{organization} " f"({abbreviation})"

    # --------------------------------------------------------
    # Explicit Company:
    # --------------------------------------------------------
    match = re.search(
        r"(?:^|\n)\s*Company\s*:\s*([^\n]+)",
        text,
        re.IGNORECASE,
    )

    if match:
        value = clean_value(match.group(1))

        if 2 <= len(value) <= 100 and len(value.split()) <= 12:
            return value

    # --------------------------------------------------------
    # Known domains
    # --------------------------------------------------------
    domain = extract_domain(url)

    if domain in KNOWN_DOMAINS:
        return KNOWN_DOMAINS[domain]

    # --------------------------------------------------------
    # Conservative "At Company,"
    # --------------------------------------------------------
    match = re.search(
        r"\bAt\s+([A-Z][A-Za-z0-9&.'\- ]{2,70}),",
        text,
    )

    if match:
        value = clean_value(match.group(1))

        if 2 <= len(value) <= 80:
            return value

    return ""


# ============================================================
# Location
# ============================================================


def extract_location(
    text: str,
) -> str:

    # Only capture a single line.
    patterns = [
        r"(?:^|\n)\s*Location\s*:\s*([^\n]+)",
        r"(?:^|\n)\s*Job Location\s*:\s*([^\n]+)",
        r"(?:^|\n)\s*Work Location\s*:\s*([^\n]+)",
        r"(?:^|\n)\s*Remote Locations?\s*:\s*([^\n]+)",
        r"(?:^|\n)\s*Location of Workplace\s*:\s*([^\n]+)",
        r"\bThis position will be located\s+(?:onsite\s+)?in\s+([^.\n]+)",
    ]

    for pattern in patterns:
        match = re.search(
            pattern,
            text,
            re.IGNORECASE,
        )

        if match:
            value = clean_value(match.group(1))

            if 2 <= len(value) <= 180:
                return value

    return ""


# ============================================================
# Experience
# ============================================================


def extract_experience(
    text: str,
) -> str:

    patterns = [
        r"\b(\d+\+?\s+years?\s+of\s+(?:applicable\s+|relevant\s+)?experience)\b",
        r"\b(\d+\+?\s+years?\s+of\s+experience)\b",
        r"(?:Required Experience)\s*:\s*([^\n]+)",
        r"(?:Experience Level)\s*:\s*([^\n]+)",
    ]

    for pattern in patterns:

        match = re.search(
            pattern,
            text,
            re.IGNORECASE,
        )

        if match:
            value = clean_value(match.group(1))

            if len(value) <= 150:
                return value

    return ""


# ============================================================
# Employment type
# ============================================================


def extract_employment_type(
    text: str,
) -> str:

    normalized = text.lower()

    detected = []

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

    return ", ".join(dict.fromkeys(detected))


# ============================================================
# Salary
# ============================================================


def extract_salary(
    text: str,
) -> str:

    patterns = [
        r"(?:Salary Range|Base Pay Range|Pay Range|Salary)"
        r"\s*:\s*"
        r"([$€£]?[0-9][0-9,]*(?:\.[0-9]+)?"
        r"\s*(?:-|to)\s*"
        r"[$€£]?[0-9][0-9,]*(?:\.[0-9]+)?)",
        r"([$€£][0-9][0-9,]*(?:\.[0-9]+)?"
        r"\s*(?:-|to)\s*"
        r"[$€£]?[0-9][0-9,]*(?:\.[0-9]+)?)",
    ]

    for pattern in patterns:
        match = re.search(
            pattern,
            text,
            re.IGNORECASE,
        )

        if match:
            return clean_value(match.group(1))

    return ""


# ============================================================
# Skills
# ============================================================

SKILLS = [
    "python",
    "java",
    "javascript",
    "typescript",
    "react",
    "react.js",
    "angular",
    "vue",
    "node.js",
    "nodejs",
    "express",
    "spring boot",
    "spring",
    "sql",
    "mysql",
    "postgresql",
    "mongodb",
    "aws",
    "azure",
    "gcp",
    "docker",
    "kubernetes",
    "git",
    "linux",
    "machine learning",
    "deep learning",
    "artificial intelligence",
    "data science",
    "data engineering",
    "terraform",
    "jenkins",
    "kafka",
    "redis",
    "graphql",
    "rest api",
    "rest apis",
    "html",
    "css",
    "tailwind",
    "next.js",
    "nextjs",
    "c++",
    "c#",
    ".net",
    "excel",
]


def extract_skills(
    text: str,
) -> list[str]:

    normalized = text.lower()

    found = []

    for skill in SKILLS:

        escaped = re.escape(skill)

        if re.search(
            rf"(?<![a-z0-9]){escaped}(?![a-z0-9])",
            normalized,
        ):
            found.append(skill)

    return found


# ============================================================
# Job normalization
# ============================================================


def normalize_job(
    record: dict[str, Any],
) -> dict[str, Any]:

    source_id = clean_text(record.get("id"))

    url = clean_text(record.get("url"))

    raw_text = clean_text(record.get("text"))

    return {
        "job_id": source_id,
        "title": extract_title(
            raw_text,
            url,
        ),
        "company": extract_company(
            raw_text,
            url,
        ),
        "description": raw_text,
        "skills": extract_skills(raw_text),
        "location": extract_location(raw_text),
        "experience": extract_experience(raw_text),
        "employment_type": extract_employment_type(raw_text),
        "salary": extract_salary(raw_text),
        "url": url,
        "source_id": source_id,
        "raw_text": raw_text,
        "heuristic_score": record.get("heuristic_score"),
    }


# ============================================================
# Main
# ============================================================


def main() -> None:

    if not INPUT_FILE.exists():
        raise FileNotFoundError(f"Missing input file: {INPUT_FILE}")

    count = 0

    with (
        INPUT_FILE.open(
            "r",
            encoding="utf-8",
        ) as input_file,
        OUTPUT_FILE.open(
            "w",
            encoding="utf-8",
        ) as output_file,
    ):

        for line in input_file:

            line = line.strip()

            if not line:
                continue

            record = json.loads(line)

            job = normalize_job(record)

            output_file.write(
                json.dumps(
                    job,
                    ensure_ascii=False,
                )
                + "\n"
            )

            count += 1

    print("=" * 60)
    print("JOB NORMALIZATION COMPLETE")
    print("=" * 60)
    print(f"Input records: {count}")
    print(f"Output file:   {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
