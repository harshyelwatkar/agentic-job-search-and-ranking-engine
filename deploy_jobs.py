from job_hybrid import (
    APPLICATION,
    INSTANCE,
    TENANT,
    package,
)

from vespa.deployment import VespaCloud


def main() -> None:
    print(
        f"Deploying job-search Vespa application "
        f"to instance '{INSTANCE}'..."
    )

    vespa_cloud = VespaCloud(
        tenant=TENANT,
        application=APPLICATION,
        application_package=package,
    )

    app = vespa_cloud.deploy(
        instance=INSTANCE
    )

    print()
    print("Job Vespa deployment complete.")
    print("URL:", app.url)


if __name__ == "__main__":
    main()