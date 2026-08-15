from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Iterable

from datasets import load_dataset
from tqdm import tqdm


# ============================================================
# Configuration
# ============================================================

DATASET_NAME = "HuggingFaceFW/fineweb"
DATASET_CONFIG = "CC-MAIN-2025-08"
DATASET_SPLIT = "train"

# We do NOT scan the entire FineWeb corpus.
# We scan only the first 15,000 documents, which is the
# development corpus already used in this project.
SCAN_LIMIT = 15_000

# Number of likely job documents we want to save.
MAX_JOBS = 250

OUTPUT_FILE = (
    Path(__file__).resolve().parent
    / "candidate_jobs.jsonl"
)


# ============================================================
# Job-related signals
# ============================================================

STRONG_JOB_TERMS = [
    "job description",
    "job details",
    "job role",
    "job title",
    "apply now",
    "apply today",
    "how to apply",
    "responsibilities",
    "qualifications",
    "requirements",
    "required skills",
    "skills required",
    "experience required",
    "years of experience",
    "employment type",
    "salary range",
    "salary",
    "benefits",
    "full-time",
    "part-time",
    "internship",
    "job posting",
    "job opening",
    "career opportunity",
    "we are hiring",
    "we're hiring",
    "hiring for",
    "currently hiring",
    "open position",
    "position available",
    "vacancy",
    "vacancies",
]

JOB_PATH_TERMS = [
    "/jobs/",
    "/job/",
    "/careers/",
    "/career/",
    "/job-openings/",
    "/job-opening/",
    "/employment/",
    "/positions/",
    "/position/",
    "/vacancies/",
]


# ============================================================
# Helpers
# ============================================================

def normalize_text(value: Any) -> str:
    if value is None:
        return ""

    text = str(value).lower()

    text = re.sub(
        r"\s+",
        " ",
        text,
    )

    return text.strip()


def calculate_job_score(
    text: str,
    url: str,
) -> tuple[int, list[str]]:
    """
    Assign a simple heuristic score.

    This is NOT a machine-learning classifier.
    It is only used to identify candidate job pages
    for manual inspection.
    """

    normalized_text = normalize_text(text)
    normalized_url = normalize_text(url)

    score = 0
    matched_signals: list[str] = []

    for term in STRONG_JOB_TERMS:
        if term in normalized_text:
            score += 1
            matched_signals.append(
                f"text:{term}"
            )

    for term in JOB_PATH_TERMS:
        if term in normalized_url:
            score += 3
            matched_signals.append(
                f"url:{term}"
            )

    return score, matched_signals


def is_candidate_job(
    text: str,
    url: str,
) -> tuple[bool, int, list[str]]:

    score, signals = calculate_job_score(
        text,
        url,
    )

    # At least one strong combination is required.
    #
    # Examples:
    #   URL contains /jobs/ + one job term
    #   several strong hiring-related terms
    #
    is_candidate = score >= 4

    return (
        is_candidate,
        score,
        signals,
    )


def stream_documents() -> Iterable[dict[str, Any]]:
    print("Connecting to FineWeb...")

    dataset = load_dataset(
        DATASET_NAME,
        DATASET_CONFIG,
        split=DATASET_SPLIT,
        streaming=True,
    )

    print("FineWeb stream connected.")

    return dataset


# ============================================================
# Extraction
# ============================================================

def main() -> None:

    dataset = stream_documents()

    candidates: list[dict[str, Any]] = []

    scanned = 0
    accepted = 0

    print()
    print(
        f"Scanning first {SCAN_LIMIT:,} FineWeb documents "
        f"for likely job postings..."
    )
    print(
        f"Target candidate jobs: {MAX_JOBS}"
    )
    print()

    for document in tqdm(
        dataset,
        total=SCAN_LIMIT,
        desc="Scanning documents",
    ):

        if scanned >= SCAN_LIMIT:
            break

        scanned += 1

        document_id = (
            document.get("id")
            or str(scanned)
        )

        text = (
            document.get("text")
            or ""
        )

        url = (
            document.get("url")
            or ""
        )

        is_candidate, score, signals = (
            is_candidate_job(
                text=text,
                url=url,
            )
        )

        if not is_candidate:
            continue

        # Keep the raw source information.
        #
        # We are intentionally NOT trying to extract
        # title/company/location/etc. yet.
        candidate = {
            "id": str(document_id),
            "url": str(url),
            "text": str(text),
            "heuristic_score": score,
            "matched_signals": signals,
        }

        candidates.append(candidate)
        accepted += 1

        # Stop once we have enough candidates.
        if accepted >= MAX_JOBS:
            break

    # Highest scoring documents first.
    candidates.sort(
        key=lambda item: item["heuristic_score"],
        reverse=True,
    )

    OUTPUT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with OUTPUT_FILE.open(
        "w",
        encoding="utf-8",
    ) as output:

        for item in candidates:
            output.write(
                json.dumps(
                    item,
                    ensure_ascii=False,
                )
                + "\n"
            )

    # ========================================================
    # Summary
    # ========================================================

    print()
    print("=" * 60)
    print("JOB CANDIDATE EXTRACTION COMPLETE")
    print("=" * 60)

    print(
        f"Documents scanned:     {scanned:,}"
    )

    print(
        f"Candidate job pages:   {len(candidates):,}"
    )

    print(
        f"Output file:            {OUTPUT_FILE}"
    )

    if candidates:
        print()
        print("Top candidate examples:")
        print("-" * 60)

        for index, item in enumerate(
            candidates[:10],
            start=1,
        ):
            print()
            print(
                f"{index}. "
                f"Score={item['heuristic_score']}"
            )

            print(
                f"URL: {item['url']}"
            )

            print(
                "Signals:",
                ", ".join(
                    item["matched_signals"][:8]
                ),
            )

            preview = (
                item["text"]
                .replace("\n", " ")
                .strip()
            )

            if len(preview) > 300:
                preview = preview[:300] + "..."

            print(
                f"Preview: {preview}"
            )

    else:
        print()
        print(
            "No candidate job pages were found."
        )


if __name__ == "__main__":
    main()