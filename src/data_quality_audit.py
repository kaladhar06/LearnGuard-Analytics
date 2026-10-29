
import csv
from pathlib import Path

from src.db_connection import get_connection

STAGING_DATABASE = "learnguard_staging"
REPORT_PATH = Path("reports") / "data_quality_impact_audit.csv"

REPORT_COLUMNS = [
    "anomaly_type",
    "detected_count",
    "metric",
    "before",
    "after",
    "impact",
    "action",
]


def add_result(results, anomaly_type, detected_count, metric,
               before, after, impact, action):
    results.append({
        "anomaly_type": anomaly_type,
        "detected_count": detected_count,
        "metric": metric,
        "before": before,
        "after": after,
        "impact": impact,
        "action": action,
    })


def audit_duplicate_events(cursor, results, raw_events):
    cursor.execute("""
        SELECT COUNT(*), COALESCE(SUM(n - 1), 0)
        FROM (
            SELECT idempotency_key, COUNT(*) AS n
            FROM ActivityEvent
            WHERE idempotency_key IS NOT NULL
            GROUP BY idempotency_key
            HAVING COUNT(*) > 1
        ) d
    """)
    groups, excess = cursor.fetchone()

    cursor.execute("""
        SELECT COUNT(DISTINCT idempotency_key)
        FROM ActivityEvent
        WHERE idempotency_key IS NOT NULL
    """)
    distinct_keys = cursor.fetchone()[0]

    add_result(
        results, "duplicate_event", groups, "logical_activity_events",
        raw_events, raw_events - excess,
        f"{excess} excess row(s) across {groups} repeated key group(s); "
        f"{distinct_keys} distinct non-null idempotency keys.",
        "Deduplicate by idempotency key for logical activity metrics. "
        "Preserve source records and investigate null keys separately."
    )


def audit_unenrolled_activity(cursor, results, raw_events):
    # Only events with a learner and a known content item can be
    # evaluated using the content-to-course enrollment relationship.
    # Assessment submissions without content_id are not automatically
    # invalid; they are checked separately through their enrollment.
    cursor.execute("""
        SELECT COUNT(*)
        FROM ActivityEvent e
        JOIN ContentItem ci
          ON ci.content_id = e.content_id
        WHERE e.learner_id IS NOT NULL
          AND (
              NOT EXISTS (
                  SELECT 1
                  FROM Enrollment en
                  WHERE en.learner_id = e.learner_id
                    AND en.course_id = ci.course_id
              )
              OR (
                  e.enrollment_id IS NOT NULL
                  AND NOT EXISTS (
                      SELECT 1
                      FROM Enrollment en2
                      WHERE en2.enrollment_id = e.enrollment_id
                        AND en2.learner_id = e.learner_id
                        AND en2.course_id = ci.course_id
                  )
              )
          )
    """)
    invalid_content_events = cursor.fetchone()[0]

    # Check events explicitly marked as unenrolled, including events
    # without content_id. Use the label as supporting evidence, while
    # the relationship check above identifies actual content mismatches.
    cursor.execute("""
        SELECT COUNT(*)
        FROM ActivityEvent e
        WHERE e.issue_type = 'unenrolled_activity'
          AND e.learner_id IS NOT NULL
          AND NOT EXISTS (
              SELECT 1
              FROM Enrollment en
              WHERE en.learner_id = e.learner_id
                AND (
                    e.enrollment_id IS NULL
                    OR en.enrollment_id = e.enrollment_id
                )
                AND (
                    e.content_id IS NULL
                    OR EXISTS (
                        SELECT 1
                        FROM ContentItem ci
                        WHERE ci.content_id = e.content_id
                          AND ci.course_id = en.course_id
                    )
                )
          )
    """)
    explicitly_unenrolled = cursor.fetchone()[0]

    invalid_events = max(invalid_content_events, explicitly_unenrolled)

    add_result(
        results, "unenrolled_activity", invalid_events,
        "eligible_activity_rows", raw_events, raw_events - invalid_events,
        f"{invalid_events} event(s) failed the learner-enrollment "
        "relationship check. Events without content_id are not rejected "
        "solely because that field is NULL.",
        "Exclude or quarantine confirmed invalid events from "
        "enrollment-based metrics. Preserve source records."
    )


def audit_premature_completion(cursor, results):
    cursor.execute("""
        SELECT COUNT(*)
        FROM CourseOutcome co
        WHERE co.outcome_status = 'completed'
          AND co.assessment_passed = 1
          AND EXISTS (
              SELECT 1
              FROM Attempt a
              JOIN Assessment s
                ON s.assessment_id = a.assessment_id
              WHERE a.enrollment_id = co.enrollment_id
                AND a.attempt_status = 'graded'
                AND a.score >= s.passing_score
                AND a.submitted_at > co.calculated_at
          )
          AND NOT EXISTS (
              SELECT 1
              FROM Attempt a2
              JOIN Assessment s2
                ON s2.assessment_id = a2.assessment_id
              WHERE a2.enrollment_id = co.enrollment_id
                AND a2.attempt_status = 'graded'
                AND a2.score >= s2.passing_score
                AND a2.submitted_at <= co.calculated_at
          )
    """)
    count = cursor.fetchone()[0]

    add_result(
        results, "premature_completion", count,
        "eligible_completion_records", count, 0,
        f"{count} completed outcome(s) have a passing graded attempt "
        "only after the recorded completion timestamp.",
        "Recalculate completion using assessment timestamps and "
        "applicable completion rules. Preserve source records."
    )


def audit_timezone_shift(cursor, results):
    cursor.execute("""
        SELECT COUNT(*)
        FROM ActivityEvent
        WHERE issue_type = 'timezone_shift'
          AND event_time_utc IS NOT NULL
          AND DATE(event_time_utc) <>
              DATE(DATE_ADD(event_time_utc, INTERVAL 330 MINUTE))
    """)
    count = cursor.fetchone()[0]

    add_result(
        results, "timezone_shift", count, "reporting_day_mismatches",
        count, 0,
        f"{count} flagged event(s) cross a calendar-day boundary "
        "between UTC and Asia/Kolkata.",
        "Keep timestamps in UTC and convert to Asia/Kolkata for "
        "reporting dates. Do not delete events."
    )


def save_report(results):
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with REPORT_PATH.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=REPORT_COLUMNS)
        writer.writeheader()
        writer.writerows(results)


def main():
    connection = None
    cursor = None

    try:
        connection = get_connection(database=STAGING_DATABASE)
        cursor = connection.cursor()
        cursor.execute("SELECT DATABASE()")
        database = cursor.fetchone()[0]

        if database != STAGING_DATABASE:
            raise RuntimeError(
                f"Safety check failed: connected to {database}, "
                f"expected {STAGING_DATABASE}."
            )

        cursor.execute("SELECT COUNT(*) FROM ActivityEvent")
        raw_events = cursor.fetchone()[0]

        cursor.execute("""
            SELECT COUNT(*)
            FROM ActivityEvent
            WHERE event_id LIKE 'EVT-%'
        """)
        baseline_events = cursor.fetchone()[0]

        results = []
        audit_duplicate_events(cursor, results, raw_events)
        audit_unenrolled_activity(cursor, results, raw_events)
        audit_premature_completion(cursor, results)
        audit_timezone_shift(cursor, results)

        print()
        print("LEARNGUARD ANALYTICS - DATA QUALITY IMPACT AUDIT")
        print("=" * 60)
        print(f"Database: {database}")
        print(f"Total activity rows: {raw_events:,}")
        print(f"Baseline activity rows: {baseline_events:,}")

        for result in results:
            print(f"\nAnomaly: {result['anomaly_type']}")
            print(f"Detected: {result['detected_count']}")
            print(f"Metric: {result['metric']}")
            print(f"Before: {result['before']}")
            print(f"After: {result['after']}")
            print(f"Impact: {result['impact']}")
            print(f"Action: {result['action']}")

        save_report(results)
        print("\n" + "=" * 60)
        print(f"Report saved to: {REPORT_PATH.resolve()}")

    except Exception as error:
        print(f"Audit failed: {error}")
        raise

    finally:
        if cursor is not None:
            cursor.close()
        if connection is not None:
            connection.close()


if __name__ == "__main__":
    main()
