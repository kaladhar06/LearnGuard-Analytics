
import csv
import hashlib
import json
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path

from src.db_connection import get_connection


DATABASE = "learnguard_staging"

EXPORT_DIR = Path("data/exports")
MANIFEST_FILE = Path("data/source_manifest.json")

ACTIVITY_CSV = Path("data/generated_activity_preview.csv")

TABLES = [
    "Learner",
    "Course",
    "Enrollment",
    "ContentItem",
    "ActivityEvent",
    "Assessment",
    "Attempt",
    "CompletionRule",
    "Cohort",
    "EnrollmentCohort",
    "CourseOutcome",
]


def json_value(value):
    if isinstance(value, datetime):
        return value.isoformat(sep=" ")

    if isinstance(value, date):
        return value.isoformat()

    if isinstance(value, Decimal):
        return float(value)

    return value


def file_sha256(path):
    digest = hashlib.sha256()

    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)

    return digest.hexdigest()


def activity_csv_metadata(path):
    if not path.exists():
        raise FileNotFoundError(
            f"Generated activity CSV not found: {path}"
        )

    with path.open(
        "r",
        newline="",
        encoding="utf-8"
    ) as file:
        reader = csv.reader(file)

        header = next(reader, [])

        row_count = sum(
            1 for _ in reader
        )

    if row_count != 2_000_000:
        raise RuntimeError(
            f"Expected 2,000,000 activity rows, found {row_count}"
        )

    if len(header) != 11:
        raise RuntimeError(
            f"Expected 11 activity columns, found {len(header)}"
        )

    return {
        "path": str(path).replace("\\", "/"),
        "rows": row_count,
        "columns": len(header),
        "size_bytes": path.stat().st_size,
        "sha256": file_sha256(path),
        "seed": 20261022,
        "database_written": False,
    }


def export_database_tables(cursor, manifest):
    for table in TABLES:

        cursor.execute(
            f"SELECT * FROM `{table}`"
        )

        rows = cursor.fetchall()

        columns = [
            item[0]
            for item in cursor.description
        ]

        csv_path = EXPORT_DIR / f"{table.lower()}.csv"
        json_path = EXPORT_DIR / f"{table.lower()}.json"

        # CSV export
        with csv_path.open(
            "w",
            newline="",
            encoding="utf-8-sig"
        ) as file:

            writer = csv.DictWriter(
                file,
                fieldnames=columns,
                extrasaction="ignore"
            )

            writer.writeheader()

            for row in rows:
                writer.writerow({
                    key: json_value(value)
                    for key, value in row.items()
                })

        # JSON export
        with json_path.open(
            "w",
            encoding="utf-8"
        ) as file:

            json.dump(
                [
                    {
                        key: json_value(value)
                        for key, value in row.items()
                    }
                    for row in rows
                ],
                file,
                indent=2,
                ensure_ascii=False
            )

        manifest["tables"][table] = {
            "row_count": len(rows),
            "csv_file": str(csv_path).replace("\\", "/"),
            "csv_sha256": file_sha256(csv_path),
            "json_file": str(json_path).replace("\\", "/"),
            "json_sha256": file_sha256(json_path),
        }

        print(
            f"Exported {table:<18} {len(rows):>7,} rows"
        )


def main():

    EXPORT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    MANIFEST_FILE.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    connection = get_connection(
        database=DATABASE
    )

    cursor = None

    try:

        cursor = connection.cursor(
            dictionary=True
        )

        cursor.execute(
            "SELECT DATABASE() AS db_name"
        )

        active_database = cursor.fetchone()["db_name"]

        if active_database != DATABASE:
            raise RuntimeError(
                f"Safety check failed: connected to {active_database}"
            )

        print("LEARNGUARD DATA EXPORT")
        print("=" * 55)
        print("Database:", active_database)

        manifest = {
            "project": "LearnGuard Analytics",
            "database": DATABASE,
            "exported_at_utc": datetime.now(
                timezone.utc
            ).isoformat(),

            "dataset_configuration": {
                "learners": 20000,
                "courses": 500,
                "enrollments": 100000,
                "activity_events_csv": 2000000,
            },

            "tables": {},

            "notes": [
                "Synthetic full-scale master data exported from staging.",
                "Two-million-row activity dataset is delivered separately as CSV.",
                "MySQL ActivityEvent table contains only database event records.",
                "Injected anomaly records are intentionally retained.",
                "Ground truth is maintained separately from input features.",
            ],
        }

        print("\nExporting database tables...")

        export_database_tables(
            cursor,
            manifest
        )

        print("\nVerifying generated activity CSV...")

        manifest["generated_activity_csv"] = (
            activity_csv_metadata(ACTIVITY_CSV)
        )

        print(
            "Activity CSV rows:",
            manifest["generated_activity_csv"]["rows"]
        )

        print(
            "Activity CSV SHA256:",
            manifest["generated_activity_csv"]["sha256"]
        )

        with MANIFEST_FILE.open(
            "w",
            encoding="utf-8"
        ) as file:

            json.dump(
                manifest,
                file,
                indent=2,
                ensure_ascii=False
            )

        print("\nEXPORT COMPLETED")
        print("=" * 55)

        print("Database:", DATABASE)
        print("CSV/JSON directory:", EXPORT_DIR)
        print("Source manifest:", MANIFEST_FILE)

        print("\nAll exports and manifest generated successfully.")

    finally:

        if cursor is not None:
            cursor.close()

        connection.close()


if __name__ == "__main__":
    main()
