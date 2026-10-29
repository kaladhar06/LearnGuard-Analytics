
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
    if isinstance(value, (datetime, date)):
        return value.isoformat(sep=" ") if isinstance(
            value, datetime
        ) else value.isoformat()
    if isinstance(value, Decimal):
        return float(value)
    return value


def file_sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main():
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    MANIFEST_FILE.parent.mkdir(parents=True, exist_ok=True)

    connection = get_connection(database=DATABASE)
    cursor = None

    try:
        cursor = connection.cursor(dictionary=True)
        cursor.execute("SELECT DATABASE() AS db_name")
        active_database = cursor.fetchone()["db_name"]

        if active_database != DATABASE:
            raise RuntimeError(
                f"Safety check failed: connected to {active_database}"
            )

        manifest = {
            "project": "LearnGuard Analytics",
            "database": DATABASE,
            "exported_at_utc": datetime.now(timezone.utc).isoformat(),
            "tables": {},
            "notes": [
                "Synthetic test dataset exported from staging.",
                "Injected anomaly records are intentionally retained.",
                "ground_truth.csv is maintained separately from features.",
            ],
        }

        for table in TABLES:
            cursor.execute(f"SELECT * FROM `{table}`")
            rows = cursor.fetchall()
            columns = [item[0] for item in cursor.description]

            csv_path = EXPORT_DIR / f"{table.lower()}.csv"
            json_path = EXPORT_DIR / f"{table.lower()}.json"

            with csv_path.open(
                "w", newline="", encoding="utf-8-sig"
            ) as file:
                writer = csv.DictWriter(
                    file, fieldnames=columns, extrasaction="ignore"
                )
                writer.writeheader()
                for row in rows:
                    writer.writerow({
                        key: json_value(value)
                        for key, value in row.items()
                    })

            with json_path.open(
                "w", encoding="utf-8"
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
                    ensure_ascii=False,
                )

            manifest["tables"][table] = {
                "row_count": len(rows),
                "csv_file": str(csv_path).replace("\\", "/"),
                "csv_sha256": file_sha256(csv_path),
                "json_file": str(json_path).replace("\\", "/"),
                "json_sha256": file_sha256(json_path),
            }

            print(f"Exported {table:<18} {len(rows):>7,} rows")

        with MANIFEST_FILE.open("w", encoding="utf-8") as file:
            json.dump(manifest, file, indent=2, ensure_ascii=False)

        print("\nEXPORT COMPLETED")
        print(f"CSV/JSON directory: {EXPORT_DIR}")
        print(f"Source manifest:    {MANIFEST_FILE}")

    finally:
        if cursor is not None:
            cursor.close()
        connection.close()


if __name__ == "__main__":
    main()
