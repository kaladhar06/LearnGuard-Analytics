
import csv
import hashlib
import json
from pathlib import Path

from src.db_connection import get_connection


ROOT = Path(__file__).resolve().parent
ACTIVITY_CSV = ROOT / "data" / "generated_activity_preview.csv"
BACKUP_CSV = (
    Path.home()
    / "OneDrive"
    / "Desktop"
    / "generated_activity_2million.csv"
)

EXPECTED_DB_COUNTS = {
    "Learner": 20_000,
    "Course": 500,
    "Enrollment": 100_000,
    "ContentItem": 2_000,
    "ActivityEvent": 2_003,
    "Assessment": 500,
    "Attempt": 300,
    "CompletionRule": 500,
    "CourseOutcome": 301,
    "Cohort": 19,
    "EnrollmentCohort": 100_000,
}

EXPORT_TABLES = list(EXPECTED_DB_COUNTS.keys())


def report(label, passed, details=""):
    status = "PASS" if passed else "REVIEW"
    suffix = f" — {details}" if details else ""
    print(f"[{status}] {label}{suffix}")


def sha256_file(path):
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def inspect_csv(path):
    with path.open("r", newline="", encoding="utf-8-sig") as file:
        reader = csv.reader(file)
        header = next(reader, [])
        row_count = sum(1 for _ in reader)
    return header, row_count


def check_database():
    print("\n1. STAGING DATABASE CHECK")
    connection = None
    cursor = None

    try:
        connection = get_connection(database="learnguard_staging")
        cursor = connection.cursor()

        for table, expected in EXPECTED_DB_COUNTS.items():
            cursor.execute(f"SELECT COUNT(*) FROM `{table}`")
            actual = cursor.fetchone()[0]
            report(
                f"Database table {table}",
                actual == expected,
                f"actual={actual:,}, expected={expected:,}",
            )

    except Exception as error:
        report("Database connection and counts", False, str(error))

    finally:
        if cursor:
            cursor.close()
        if connection and connection.is_connected():
            connection.close()


def check_activity_csv():
    print("\n2. TWO-MILLION-EVENT CSV CHECK")

    if not ACTIVITY_CSV.exists():
        report("Activity CSV exists", False, str(ACTIVITY_CSV))
        return

    report("Activity CSV exists", True, ACTIVITY_CSV.name)

    try:
        header, row_count = inspect_csv(ACTIVITY_CSV)
        expected_header = [
            "event_id",
            "enrollment_id",
            "content_id",
            "event_type",
            "event_time_utc",
            "received_at_utc",
            "device_type",
            "sync_status",
            "idempotency_key",
            "issue_type",
            "learner_id",
        ]

        report(
            "Activity CSV has expected columns",
            header == expected_header,
            f"columns={len(header)}",
        )
        report(
            "Activity CSV contains 2,000,000 data rows",
            row_count == 2_000_000,
            f"rows={row_count:,}",
        )

        checksum = sha256_file(ACTIVITY_CSV)
        print(f"    SHA256: {checksum}")

        if BACKUP_CSV.exists():
            backup_checksum = sha256_file(BACKUP_CSV)
            report(
                "Desktop backup matches activity CSV",
                checksum == backup_checksum,
                f"backup={BACKUP_CSV}",
            )
        else:
            report(
                "Desktop backup exists",
                False,
                f"Not found: {BACKUP_CSV}",
            )

    except Exception as error:
        report("Activity CSV inspection", False, str(error))


def check_exports():
    print("\n3. TABLE EXPORT CHECK")
    export_dir = ROOT / "data" / "exports"

    if not export_dir.exists():
        report("Exports folder exists", False, str(export_dir))
        return

    report("Exports folder exists", True)

    for table in EXPORT_TABLES:
        csv_path = export_dir / f"{table}.csv"

        if not csv_path.exists():
            report(f"{table}.csv export", False, "file missing")
            continue

        try:
            _, rows = inspect_csv(csv_path)
            expected = EXPECTED_DB_COUNTS[table]
            report(
                f"{table}.csv export",
                rows == expected,
                f"rows={rows:,}, expected={expected:,}",
            )
        except Exception as error:
            report(f"{table}.csv export", False, str(error))


def check_anomaly_artifacts():
    print("\n4. ANOMALY AND AUDIT FILES CHECK")

    ground_truth = ROOT / "data" / "ground_truth.csv"
    audit_report = ROOT / "reports" / "data_quality_impact_audit.csv"
    manifest = ROOT / "data" / "source_manifest.json"

    for path, label in [
        (ground_truth, "Ground truth CSV"),
        (audit_report, "Data quality impact audit"),
        (manifest, "Source manifest"),
    ]:
        report(label + " exists", path.exists(), str(path))

    if ground_truth.exists():
        try:
            _, rows = inspect_csv(ground_truth)
            report(
                "Ground truth contains four anomaly labels",
                rows == 4,
                f"rows={rows}",
            )
        except Exception as error:
            report("Ground truth CSV readable", False, str(error))

    if audit_report.exists():
        try:
            _, rows = inspect_csv(audit_report)
            report(
                "Impact audit contains four anomaly records",
                rows == 4,
                f"rows={rows}",
            )
        except Exception as error:
            report("Impact audit readable", False, str(error))

    if manifest.exists():
        try:
            with manifest.open("r", encoding="utf-8") as file:
                data = json.load(file)
            report(
                "Source manifest is valid JSON",
                isinstance(data, (dict, list)),
                f"type={type(data).__name__}",
            )
            if isinstance(data, dict):
                print(f"    Manifest keys: {list(data.keys())}")
        except Exception as error:
            report("Source manifest is valid JSON", False, str(error))


def main():
    print("=" * 65)
    print("LEARNGUARD ANALYTICS — FINAL READ-ONLY SUBMISSION AUDIT")
    print("=" * 65)

    check_database()
    check_activity_csv()
    check_exports()
    check_anomaly_artifacts()

    print("\n" + "=" * 65)
    print("AUDIT FINISHED — REVIEW ANY ITEMS MARKED REVIEW")
    print("This script does not insert, update, or delete database records.")
    print("=" * 65)


if __name__ == "__main__":
    main()
