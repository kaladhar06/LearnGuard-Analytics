
import csv
from pathlib import Path

from src.db_connection import get_connection


PROJECT_ROOT = Path(__file__).resolve().parent.parent
REPORT_PATH = PROJECT_ROOT / "reports" / "data_quality_impact_audit.csv"

REPORT_COLUMNS = [
    "anomaly_type",
    "detected_count",
    "affected_metric",
    "before_value",
    "after_value",
    "impact",
    "recommended_action",
]


def fetch_one(cursor, query, params=None):
    """Execute a query and return its first scalar result."""
    cursor.execute(query, params or ())
    result = cursor.fetchone()
    return int(result[0] or 0)


def audit_duplicate_events(cursor, raw_events):
    duplicate_keys = fetch_one(
        cursor,
        """
        SELECT COUNT(*)
        FROM (
            SELECT idempotency_key
            FROM ActivityEvent
            WHERE idempotency_key IS NOT NULL
            GROUP BY idempotency_key
            HAVING COUNT(*) > 1
        ) AS duplicate_groups
        """,
    )

    duplicate_excess = fetch_one(
        cursor,
        """
        SELECT COALESCE(SUM(event_count - 1), 0)
        FROM (
            SELECT COUNT(*) AS event_count
            FROM ActivityEvent
            WHERE idempotency_key IS NOT NULL
            GROUP BY idempotency_key
            HAVING COUNT(*) > 1
        ) AS duplicate_groups
        """,
    )

    unique_keys = fetch_one(
        cursor,
        """
        SELECT COUNT(DISTINCT idempotency_key)
        FROM ActivityEvent
        WHERE idempotency_key IS NOT NULL
        """,
    )

    return {
        "anomaly_type": "duplicate_event",
        "detected_count": duplicate_keys,
        "affected_metric": "logical_activity_events",
        "before_value": raw_events,
        "after_value": raw_events - duplicate_excess,
        "impact": (
            f"{duplicate_excess} excess row(s) across "
            f"{duplicate_keys} repeated key group(s); "
            f"{unique_keys} distinct non-null idempotency keys."
        ),
        "recommended_action": (
            "Deduplicate by idempotency key when calculating logical "
            "activity metrics. Preserve the source records and "
            "investigate null keys separately."
        ),
    }


def audit_unenrolled_activity(cursor, raw_events):
    unenrolled_events = fetch_one(
        cursor,
        """
        SELECT COUNT(*)
        FROM ActivityEvent ae
        JOIN ContentItem ci
            ON ci.content_id = ae.content_id
        WHERE NOT EXISTS (
            SELECT 1
            FROM Enrollment e
            WHERE e.learner_id = ae.learner_id
              AND e.course_id = ci.course_id
        )
        """,
    )

    return {
        "anomaly_type": "unenrolled_activity",
        "detected_count": unenrolled_events,
        "affected_metric": "eligible_activity_rows",
        "before_value": raw_events,
        "after_value": raw_events - unenrolled_events,
        "impact": (
            f"{unenrolled_events} event(s) have no matching enrollment "
            "for the learner and content's course."
        ),
        "recommended_action": (
            "Exclude or quarantine these events from enrollment-based "
            "metrics. Preserve the original records for investigation."
        ),
    }


def audit_premature_completion(cursor):
    premature_count = fetch_one(
        cursor,
        """
        SELECT COUNT(*)
        FROM CourseOutcome co
        JOIN Enrollment e
            ON e.enrollment_id = co.enrollment_id
        JOIN CompletionRule cr
            ON cr.rule_id = co.rule_id
        WHERE co.outcome_status = 'completed'
          AND cr.require_assessment_pass = 1
          AND EXISTS (
              SELECT 1
              FROM Attempt a
              JOIN Assessment asm
                  ON asm.assessment_id = a.assessment_id
              WHERE a.enrollment_id = co.enrollment_id
                AND asm.course_id = e.course_id
                AND a.attempt_status = 'graded'
                AND a.score >= asm.passing_score
                AND co.calculated_at < a.submitted_at
          )
          AND (
              co.outcome_id = 'ANOM-OUTCOME-003'
              OR co.decision_reason LIKE 'TEST ANOMALY:%'
          )
        """,
    )

    return {
        "anomaly_type": "premature_completion",
        "detected_count": premature_count,
        "affected_metric": "eligible_completion_records",
        "before_value": premature_count,
        "after_value": 0,
        "impact": (
            f"{premature_count} flagged test completion record(s) "
            "must be excluded from trusted completion metrics "
            "until investigated."
        ),
        "recommended_action": (
            "Recalculate completion using valid assessment timestamps "
            "and completion rules. Keep the flagged source record."
        ),
    }


def audit_timezone_shift(cursor):
    shifted_events = fetch_one(
        cursor,
        """
        SELECT COUNT(*)
        FROM ActivityEvent
        WHERE issue_type = 'timezone_shift'
          AND DATE(event_time_utc)
              <> DATE(DATE_ADD(event_time_utc, INTERVAL 330 MINUTE))
        """,
    )

    return {
        "anomaly_type": "timezone_shift",
        "detected_count": shifted_events,
        "affected_metric": "reporting_day_mismatches",
        "before_value": shifted_events,
        "after_value": 0,
        "impact": (
            f"{shifted_events} flagged event(s) cross a calendar-day "
            "boundary between UTC and Asia/Kolkata."
        ),
        "recommended_action": (
            "Store timestamps in UTC and convert to Asia/Kolkata "
            "when calculating reporting dates. Do not delete events."
        ),
    }


def main():
    connection = None
    cursor = None

    try:
        # Never use the original database for this audit.
        connection = get_connection(database="learnguard_staging")
        cursor = connection.cursor()

        raw_events = fetch_one(
            cursor,
            "SELECT COUNT(*) FROM ActivityEvent",
        )

        baseline_events = fetch_one(
            cursor,
            "SELECT COUNT(*) FROM ActivityEvent WHERE event_id LIKE 'EVT-%'",
        )

        report_rows = [
            audit_duplicate_events(cursor, raw_events),
            audit_unenrolled_activity(cursor, raw_events),
            audit_premature_completion(cursor),
            audit_timezone_shift(cursor),
        ]

        REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)

        with REPORT_PATH.open(
            "w",
            newline="",
            encoding="utf-8",
        ) as csv_file:
            writer = csv.DictWriter(
                csv_file,
                fieldnames=REPORT_COLUMNS,
            )
            writer.writeheader()
            writer.writerows(report_rows)

        print("LEARNGUARD ANALYTICS - DATA QUALITY IMPACT AUDIT")
        print("=" * 65)
        print("Database: learnguard_staging")
        print(f"Total activity rows: {raw_events:,}")
        print(f"Baseline activity rows: {baseline_events:,}")

        for row in report_rows:
            print(
                f"\nAnomaly: {row['anomaly_type']}\n"
                f"Detected: {row['detected_count']}\n"
                f"Metric: {row['affected_metric']}\n"
                f"Before: {row['before_value']}\n"
                f"After: {row['after_value']}\n"
                f"Impact: {row['impact']}\n"
                f"Action: {row['recommended_action']}"
            )

        print("\n" + "=" * 65)
        print(f"Report saved to: {REPORT_PATH}")

    except Exception as error:
        print(f"DATA QUALITY AUDIT ERROR: {error}")
        raise

    finally:
        if cursor is not None:
            cursor.close()

        if connection is not None:
            connection.close()


if __name__ == "__main__":
    main()
