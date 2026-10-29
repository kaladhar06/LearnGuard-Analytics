
import argparse
import csv
from collections import Counter
from pathlib import Path

from src.db_connection import get_connection

STAGING_DATABASE = "learnguard_staging"
PREVIEW_FILE = Path("data/generated_activity_preview.csv")
EXPECTED_BASELINE_EVENTS = 2000

DUPLICATE_EVENT_ID = (
    "EVT-ENR-LRN-000001-CRS-000009-000001"
)

EXPECTED_ACTIVITY_ANOMALIES = {
    "ANOM-DUP-EVT-ENR-LRN-000001-CRS-000009-000001":
        "duplicate_event",
    "ANOM-UNENROLLED-001": "unenrolled_activity",
    "ANOM-TIMEZONE-004": "timezone_shift",
}
OUTCOME_ANOMALY_ID = "ANOM-OUTCOME-003"


def load_preview():
    if not PREVIEW_FILE.exists():
        raise FileNotFoundError(
            f"Preview not found: {PREVIEW_FILE}"
        )

    with PREVIEW_FILE.open(
        "r", newline="", encoding="utf-8"
    ) as file:
        records = list(csv.DictReader(file))

    if len(records) != EXPECTED_BASELINE_EVENTS:
        raise ValueError(
            f"Expected {EXPECTED_BASELINE_EVENTS} preview events; "
            f"found {len(records)}."
        )

    event_ids = [row["event_id"] for row in records]

    if len(event_ids) != len(set(event_ids)):
        raise ValueError("Preview contains duplicate event IDs.")

    required_fields = [
        "event_id",
        "enrollment_id",
        "event_type",
        "event_time_utc",
        "received_at_utc",
        "device_type",
        "sync_status",
        "idempotency_key",
        "learner_id",
    ]

    for row in records:
        for field in required_fields:
            if not row.get(field):
                raise ValueError(
                    f"Missing {field} in event {row.get('event_id')}"
                )

        if row["received_at_utc"] < row["event_time_utc"]:
            raise ValueError(
                f"Received time precedes event time: {row['event_id']}"
            )

        if row["issue_type"]:
            raise ValueError(
                "Baseline preview must not contain injected anomalies."
            )

    return records

def check_staging_and_anomalies(cursor):
    cursor.execute("SELECT DATABASE() AS db_name")
    database = cursor.fetchone()["db_name"]

    if database != STAGING_DATABASE:
        raise RuntimeError(
            f"Safety check failed: connected to {database}"
        )

    cursor.execute("""
        SELECT event_id, issue_type, idempotency_key
        FROM ActivityEvent
        WHERE event_id IN (
            'ANOM-DUP-EVT-ENR-LRN-000001-CRS-000009-000001',
            'ANOM-UNENROLLED-001',
            'ANOM-TIMEZONE-004'
        )
    """)
    rows = cursor.fetchall()

    found = {row["event_id"]: row for row in rows}

    if set(found) != set(EXPECTED_ACTIVITY_ANOMALIES):
        raise RuntimeError(
            "Expected activity anomalies are missing. Stop."
        )

    for event_id, expected_issue in EXPECTED_ACTIVITY_ANOMALIES.items():
        if found[event_id]["issue_type"] != expected_issue:
            raise RuntimeError(
                f"Unexpected issue_type for {event_id}"
            )

    cursor.execute("""
        SELECT outcome_id
        FROM CourseOutcome
        WHERE outcome_id = %s
    """, (OUTCOME_ANOMALY_ID,))

    if cursor.fetchone() is None:
        raise RuntimeError(
            "Premature-completion anomaly is missing. Stop."
        )

    cursor.execute("""
        SELECT *
        FROM ActivityEvent
        WHERE event_id = %s
    """, (DUPLICATE_EVENT_ID,))

    original = cursor.fetchone()

    if original is None:
        raise RuntimeError(
            "Original event behind the duplicate is missing."
        )

    duplicate_id = (
        "ANOM-DUP-EVT-ENR-LRN-000001-CRS-000009-000001"
    )

    cursor.execute("""
        SELECT idempotency_key
        FROM ActivityEvent
        WHERE event_id = %s
    """, (duplicate_id,))

    duplicate = cursor.fetchone()

    if (
        duplicate is None
        or duplicate["idempotency_key"]
        != original["idempotency_key"]
    ):
        raise RuntimeError(
            "The original and duplicate no longer share their key."
        )

    return original


def validate_preview_against_database(cursor, records):
    cursor.execute("""
        SELECT
            enrollment_id,
            learner_id,
            course_id,
            enrolled_at
        FROM Enrollment
    """)
    enrollments = {
        row["enrollment_id"]: row
        for row in cursor.fetchall()
    }

    cursor.execute("""
        SELECT content_id, course_id, content_type
        FROM ContentItem
    """)
    content = {
        row["content_id"]: row
        for row in cursor.fetchall()
    }

    for row in records:
        enrollment = enrollments.get(row["enrollment_id"])

        if enrollment is None:
            raise ValueError(
                f"Unknown enrollment: {row['enrollment_id']}"
            )

        if enrollment["learner_id"] != row["learner_id"]:
            raise ValueError(
                f"Learner/enrollment mismatch: {row['event_id']}"
            )

        event_time = row["event_time_utc"]
        enrolled_at = enrollment["enrolled_at"].strftime(
            "%Y-%m-%d %H:%M:%S"
        )

        if event_time < enrolled_at:
            raise ValueError(
                f"Event predates enrollment: {row['event_id']}"
            )

        content_id = row["content_id"]

        if content_id:
            item = content.get(content_id)

            if item is None:
                raise ValueError(
                    f"Unknown content ID in {row['event_id']}"
                )

            if item["course_id"] != enrollment["course_id"]:
                raise ValueError(
                    f"Content belongs to another course: "
                    f"{row['event_id']}"
                )

            if (
                row["event_type"] == "video_progress"
                and item["content_type"] != "video"
            ):
                raise ValueError(
                    f"Video event references non-video content: "
                    f"{row['event_id']}"
                )


def rebuild_activity(cursor, preview, original):
    # Preserve the original event and its matching anomaly.
    # Remove only ordinary baseline rows, never flagged anomalies.
    cursor.execute("""
        DELETE FROM ActivityEvent
        WHERE event_id LIKE 'EVT-%'
          AND event_id <> %s
    """, (DUPLICATE_EVENT_ID,))

    # If the preview contains the original event ID, exclude it.
    # The database's original row is already being preserved.
    additional = [
        row for row in preview
        if row["event_id"] != DUPLICATE_EVENT_ID
    ][:EXPECTED_BASELINE_EVENTS - 1]

    if len(additional) != EXPECTED_BASELINE_EVENTS - 1:
        raise RuntimeError(
            "Could not prepare exactly 1,999 additional baseline events."
        )

    columns = [
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

    sql = (
        "INSERT INTO ActivityEvent ("
        + ", ".join(columns)
        + ") VALUES ("
        + ", ".join(["%s"] * len(columns))
        + ")"
    )

    values = [
        tuple(row[column] or None for column in columns)
        for row in additional
    ]

    cursor.executemany(sql, values)


def repair_attempt_timestamps(cursor):
    # Move only attempts that predate enrollment.
    # Keep their scores, attempt IDs, and attempt numbers unchanged.
    cursor.execute("""
        UPDATE Attempt a
        JOIN Enrollment e
          ON e.enrollment_id = a.enrollment_id
        SET a.submitted_at = DATE_ADD(e.enrolled_at, INTERVAL 1 DAY)
        WHERE a.submitted_at < e.enrolled_at
    """)

    return cursor.rowcount


def recalculate_normal_outcomes(cursor):
    cursor.execute("""
        SELECT
            e.enrollment_id,
            e.course_id
        FROM Enrollment e
        ORDER BY e.enrollment_id
    """)
    enrollments = cursor.fetchall()

    cursor.execute("""
        SELECT course_id, COUNT(*) AS required_items
        FROM ContentItem
        WHERE content_type IN ('video', 'reading', 'exercise')
        GROUP BY course_id
    """)
    required_items = {
        row["course_id"]: row["required_items"]
        for row in cursor.fetchall()
    }

    cursor.execute("""
        SELECT
            a.enrollment_id,
            COUNT(DISTINCT a.content_id) AS completed_items
        FROM ActivityEvent a
        JOIN Enrollment e
          ON e.enrollment_id = a.enrollment_id
        JOIN ContentItem c
          ON c.content_id = a.content_id
         AND c.course_id = e.course_id
        WHERE a.event_type = 'content_complete'
          AND c.content_type IN ('video', 'reading', 'exercise')
          AND a.issue_type IS NULL
        GROUP BY a.enrollment_id
    """)
    completed_items = {
        row["enrollment_id"]: row["completed_items"]
        for row in cursor.fetchall()
    }

    cursor.execute("""
        SELECT
            e.enrollment_id,
            MAX(
                CASE
                    WHEN a.score >= s.passing_score
                     AND a.attempt_status <> 'voided'
                    THEN 1 ELSE 0
                END
            ) AS passed,
            COUNT(a.attempt_id) AS attempt_count
        FROM Enrollment e
        LEFT JOIN Attempt a
          ON a.enrollment_id = e.enrollment_id
        LEFT JOIN Assessment s
          ON s.assessment_id = a.assessment_id
         AND s.course_id = e.course_id
        GROUP BY e.enrollment_id
    """)
    attempt_summary = {
        row["enrollment_id"]: row
        for row in cursor.fetchall()
    }

    cursor.execute("""
        SELECT rule_id, course_id,
               min_content_completion_pct,
               require_assessment_pass
        FROM CompletionRule
    """)
    rules_by_course = {
        row["course_id"]: row
        for row in cursor.fetchall()
    }

    cursor.execute("""
        SELECT outcome_id, enrollment_id, rule_id
        FROM CourseOutcome
        WHERE outcome_id LIKE 'OUT-%'
    """)
    normal_outcomes = cursor.fetchall()

    updates = []

    enrollment_by_id = {
        row["enrollment_id"]: row
        for row in enrollments
    }

    for outcome in normal_outcomes:
        enrollment = enrollment_by_id.get(
            outcome["enrollment_id"]
        )

        if enrollment is None:
            raise RuntimeError(
                f"Outcome has unknown enrollment: {outcome['outcome_id']}"
            )

        rule = rules_by_course.get(enrollment["course_id"])

        if rule is None or rule["rule_id"] != outcome["rule_id"]:
            raise RuntimeError(
                f"Outcome rule/course mismatch: {outcome['outcome_id']}"
            )

        total = required_items.get(enrollment["course_id"], 0)
        completed = completed_items.get(
            enrollment["enrollment_id"], 0
        )

        percentage = (
            min(100.0, completed * 100.0 / total)
            if total else 0.0
        )

        summary = attempt_summary.get(
            enrollment["enrollment_id"], {}
        )
        passed = int(summary.get("passed") or 0)
        attempts = int(summary.get("attempt_count") or 0)

        content_met = (
            percentage >= float(
                rule["min_content_completion_pct"]
            )
        )
        assessment_met = (
            not bool(rule["require_assessment_pass"])
            or passed == 1
        )

        if content_met and assessment_met:
            status = "completed"
            reason = (
                "Required content threshold and assessment rule met."
            )
        elif percentage > 0 or attempts > 0:
            status = "in_progress"
            reason = (
                "Activity or assessment exists; completion criteria "
                "are not all met."
            )
        else:
            status = "not_completed"
            reason = "No qualifying content or assessment activity."

        updates.append((
            round(percentage, 2),
            passed,
            status,
            reason,
            outcome["outcome_id"],
        ))

    cursor.executemany("""
        UPDATE CourseOutcome
        SET content_completion_pct = %s,
            assessment_passed = %s,
            outcome_status = %s,
            decision_reason = %s
        WHERE outcome_id = %s
    """, updates)

    return len(updates)


def validate_after_rebuild(cursor):
    cursor.execute("""
        SELECT COUNT(*) AS total
        FROM ActivityEvent
        WHERE event_id LIKE 'EVT-%'
    """)
    baseline_count = cursor.fetchone()["total"]

    if baseline_count != EXPECTED_BASELINE_EVENTS:
        raise RuntimeError(
            f"Expected 2,000 baseline events; found {baseline_count}."
        )

    cursor.execute("""
        SELECT COUNT(*) AS total
        FROM ActivityEvent
        WHERE issue_type IS NOT NULL
    """)
    flagged_count = cursor.fetchone()["total"]

    if flagged_count != 3:
        raise RuntimeError(
            f"Expected 3 flagged activity anomalies; found {flagged_count}."
        )

    cursor.execute("""
        SELECT COUNT(*) AS total
        FROM Attempt a
        JOIN Enrollment e
          ON e.enrollment_id = a.enrollment_id
        WHERE a.submitted_at < e.enrolled_at
    """)
    invalid_attempts = cursor.fetchone()["total"]

    if invalid_attempts:
        raise RuntimeError(
            f"{invalid_attempts} attempts still predate enrollment."
        )

    cursor.execute("""
        SELECT COUNT(*) AS total
        FROM ActivityEvent
        WHERE idempotency_key IN (
            SELECT idempotency_key
            FROM ActivityEvent
            GROUP BY idempotency_key
            HAVING COUNT(*) > 1
        )
    """)
    duplicate_rows = cursor.fetchone()["total"]

    if duplicate_rows != 2:
        raise RuntimeError(
            "Expected exactly one duplicate key shared by two rows; "
            f"found {duplicate_rows} rows with repeated keys."
        )

    cursor.execute("""
        SELECT COUNT(*) AS total
        FROM CourseOutcome
        WHERE outcome_id = %s
    """, (OUTCOME_ANOMALY_ID,))

    if cursor.fetchone()["total"] != 1:
        raise RuntimeError(
            "Premature-completion anomaly was not preserved."
        )

    cursor.execute("""
        SELECT COUNT(*) AS total
        FROM ActivityEvent
        WHERE event_id IN (
            'ANOM-DUP-EVT-ENR-LRN-000001-CRS-000009-000001',
            'ANOM-UNENROLLED-001',
            'ANOM-TIMEZONE-004'
        )
    """)

    if cursor.fetchone()["total"] != 3:
        raise RuntimeError(
            "One or more labelled activity anomalies are missing."
        )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Apply the rebuild to staging. Omit for dry run.",
    )
    args = parser.parse_args()

    preview = load_preview()
    connection = None
    cursor = None

    try:
        connection = get_connection(database=STAGING_DATABASE)
        cursor = connection.cursor(dictionary=True)

        original = check_staging_and_anomalies(cursor)
        validate_preview_against_database(cursor, preview)

        print("LEARNGUARD CONTROLLED REBUILD")
        print("=" * 40)
        print(f"Database:                 {STAGING_DATABASE}")
        print(f"Preview events:           {len(preview):,}")
        print(f"Unique event IDs:         {len(set(r['event_id'] for r in preview)):,}")
        print("Original duplicate pair:  verified")
        print("Four labelled anomalies:  verified")
        print(f"Mode:                     {'APPLY' if args.apply else 'DRY RUN'}")

        if not args.apply:
            print("\nDry run passed. No database changes were made.")
            print("Review the script, then run with --apply to rebuild staging.")
            return

        # Reuse the connection's existing transaction.
# Do not start a second transaction.

        try:
            rebuild_activity(cursor, preview, original)
            repaired_attempts = repair_attempt_timestamps(cursor)
            recalculated = recalculate_normal_outcomes(cursor)
            validate_after_rebuild(cursor)

            connection.commit()

            print("\nREBUILD COMMITTED SUCCESSFULLY")
            print(f"Baseline events:          {EXPECTED_BASELINE_EVENTS:,}")
            print(f"Attempt timestamps fixed: {repaired_attempts}")
            print(f"Normal outcomes updated:  {recalculated}")
            print("All post-rebuild checks passed.")

        except Exception:
            connection.rollback()
            print("\nREBUILD FAILED — transaction rolled back.")
            raise

    finally:
        if cursor is not None:
            cursor.close()
        if connection is not None:
            connection.close()


if __name__ == "__main__":
    main()
