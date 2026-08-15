from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from vespa.deployment import VespaCloud


TENANT = "agentic-search"
APPLICATION = "agenticjobsearch"
INSTANCE = "jobs-clean"

PROJECT_ROOT = Path(__file__).resolve().parent
JOBS_FILE = PROJECT_ROOT / "job_data" / "jobs_clean.jsonl"


def load_jobs() -> list[dict[str, Any]]:
    if not JOBS_FILE.exists():
        raise FileNotFoundError(
            f"Jobs file not found: {JOBS_FILE}"
        )

    jobs: list[dict[str, Any]] = []

    with JOBS_FILE.open(
        "r",
        encoding="utf-8",
    ) as file:
        for line in file:
            line = line.strip()

            if line:
                jobs.append(json.loads(line))

    return jobs


def build_search_text(
    job: dict[str, Any]
) -> str:

    skills = job.get("skills") or []

    if isinstance(skills, list):
        skills_text = ", ".join(
            str(skill)
            for skill in skills
        )
    else:
        skills_text = str(skills)

    parts = [
        job.get("title", ""),
        job.get("company", ""),
        skills_text,
        job.get("location", ""),
        job.get("experience", ""),
        job.get("employment_type", ""),
        job.get("salary", ""),
        job.get("description", ""),
    ]

    return " | ".join(
        str(part).strip()
        for part in parts
        if str(part).strip()
    )


def build_document(
    job: dict[str, Any]
) -> dict[str, Any]:

    job_id = str(
        job.get("job_id")
        or job.get("source_id")
        or ""
    )

    skills = job.get("skills") or []

    if not isinstance(skills, list):
        skills = [str(skills)]

    return {
        "id": job_id,
        "fields": {
            "job_id": job_id,
            "title": str(
                job.get("title") or ""
            ),
            "company": str(
                job.get("company") or ""
            ),
            "description": str(
                job.get("description") or ""
            ),
            "skills": [
                str(skill)
                for skill in skills
                if str(skill).strip()
            ],
            "location": str(
                job.get("location") or ""
            ),
            "experience": str(
                job.get("experience") or ""
            ),
            "employment_type": str(
                job.get("employment_type") or ""
            ),
            "salary": str(
                job.get("salary") or ""
            ),
            "url": str(
                job.get("url") or ""
            ),
            "search_text": build_search_text(
                job
            ),
        },
    }


def main() -> None:

    print("Loading normalized job dataset...")

    jobs = load_jobs()

    print(
        f"Loaded {len(jobs):,} jobs."
    )

    print(
        f"Connecting to Vespa Cloud "
        f"instance '{INSTANCE}'..."
    )

    vespa_cloud = VespaCloud(
        tenant=TENANT,
        application=APPLICATION,
        application_package=package_from_disk(),
    )

    app = vespa_cloud.get_application(
        instance=INSTANCE
    )

    print("Connected to:", app.url)

    successful = 0
    failed = 0

    print()
    print(
        f"Feeding {len(jobs):,} job documents..."
    )

    with app.syncio(
        connections=4
    ) as session:

        for index, job in enumerate(
            jobs,
            start=1,
        ):

            document = build_document(
                job
            )

            try:
                response = session.feed_data_point(
                    data_id=document["id"],
                    fields=document["fields"],
                    schema="job",
                )

                if (
                    hasattr(
                        response,
                        "is_successful",
                    )
                    and not response.is_successful()
                ):
                    failed += 1

                    print(
                        f"[ERROR] "
                        f"{index}/{len(jobs)} "
                        f"{document['id']}: "
                        f"{response}"
                    )

                    continue

                successful += 1

            except Exception as exc:
                failed += 1

                print(
                    f"[ERROR] "
                    f"{index}/{len(jobs)} "
                    f"{document['id']}: "
                    f"{exc}"
                )

                continue

            if (
                index == 1
                or index % 10 == 0
                or index == len(jobs)
            ):
                print(
                    f"Progress: "
                    f"{index}/{len(jobs)} "
                    f"| Successful: {successful} "
                    f"| Errors: {failed}"
                )

    print()
    print("=" * 60)
    print("JOB INGESTION COMPLETE")
    print("=" * 60)
    print(
        f"Successful: {successful}"
    )
    print(
        f"Errors:     {failed}"
    )
    print("=" * 60)


def package_from_disk():
    """
    Job feeding does not need to deploy the package.

    The job application must already be deployed in the
    'jobs' instance. We provide a minimal ApplicationPackage
    only because this PyVespa version requires one when
    constructing VespaCloud.
    """
    from vespa.package import ApplicationPackage

    return ApplicationPackage(
        name=APPLICATION
    )


if __name__ == "__main__":
    main()