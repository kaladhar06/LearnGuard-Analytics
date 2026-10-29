
import csv
from pathlib import Path
from datetime import datetime

from src.db_connection import get_connection


GROUND_TRUTH_PATH = Path("data/ground_truth.csv")


def inject_premature_completion(cursor):
    """
    Create an outcome that claims completion before the required
    assessment pass. The recorded completion time is intentionally
    earlier than the passing assessment attempt.
    """

    cursor.execute("""
        SELECT
            e.enrollment_id,
            e.course_id,
            cr.rule_id,
            a.assessment_id
        FROM Enrollment e
        JOIN CompletionRule cr
            ON cr.course_id = e.course_id
           AND cr.require_assessment_pass = 1
        JOIN Assessment a
            ON a.course_id = e.course_id
        JOIN Attempt att
            ON att.enrollment_id = e.enrollment_id
           AND att.assessment_id = a.assessment_id
           AND att.score >= a.passing_score
           AND att.attempt_status = 'graded'
        WHERE NOT EXISTS (
            SELECT 1
            FROM CourseOutcome co
            WHERE co.enrollment_id = e.enrollment_id
              AND co.outcome_id = 'ANOM-OUTCOME-003'
        )
        ORDER BY e.enrollment_id
        LIMIT 1
    """)

    result = cursor.fetchone()

    if not result:
        raise RuntimeError(
            "No enrollment with a passing graded attempt was found. "
            "We need to inspect the assessment data before creating "
            "the premature-completion scenario."
        )

    enrollment_id, course_id, rule_id, assessment_id = result

    # Choose a time earlier than the passing attempt.
    cursor.execute("""
        SELECT MIN(att.submitted_at)
        FROM Attempt att
        WHERE att.enrollment_id = %s
          AND att.assessment_id = %s
          AND att.attempt_status = 'graded'
          AND att.score >= (
              SELECT passing_score
              FROM Assessment
              WHERE assessment_id = %s
          )
    """, (enrollment_id, assessment_id, assessment_id))

    passing_time = cursor.fetchone()[0]

    if passing_time is None:
        raise RuntimeError("Passing assessment timestamp not found.")

    completion_time = passing_time.replace(year=passing_time.year - 1)

    cursor.execute("""
        SELECT COUNT(*)
        FROM CourseOutcome
        WHERE outcome_id = 'ANOM-OUTCOME-003'
    """)

    if cursor.fetchone()[0] == 0:
        cursor.execute("""
            INSERT INTO CourseOutcome (
                outcome_id,
                enrollment_id,
                rule_id,
                calculated_at,
                content_completion_pct,
                assessment_passed,
                outcome_status,
                decision_reason
            )
            VALUES (
                'ANOM-OUTCOME-003',
                %s,
                %s,
                %s,
                100.00,
                1,
                'completed',
                'TEST ANOMALY: completion recorded before assessment pass'
            )
        """, (enrollment_id, rule_id, completion_time))

    print(
        "Premature-completion test case:",
        "ANOM-OUTCOME-003",
        "| enrollment:",
        enrollment_id,
        "| assessment:",
        assessment_id,
    )

    return "ANOM-OUTCOME-003"


def inject_timezone_shift(cursor):
    """
    Create an event close to midnight UTC so its UTC date differs
    from the reporting date in India (UTC+05:30).
    """

    event_id = "ANOM-TIMEZONE-004"

    cursor.execute(
        "SELECT event_id FROM ActivityEvent WHERE event_id = %s",
        (event_id,),
    )

    if cursor.fetchone():
        print("Timezone-shift test case already exists.")
        return event_id

    cursor.execute("""
        SELECT
            e.enrollment_id,
            e.learner_id,
            ci.content_id
        FROM Enrollment e
        JOIN ContentItem ci
            ON ci.course_id = e.course_id
        ORDER BY e.enrollment_id, ci.content_id
        LIMIT 1
    """)

    result = cursor.fetchone()

    if not result:
        raise RuntimeError(
            "No valid enrollment and content item found."
        )

    enrollment_id, learner_id, content_id = result

    # 2026-10-20 22:45 UTC becomes 2026-10-21 04:15 in India.
    event_time = datetime(2026, 10, 20, 22, 45, 0)
    received_time = datetime(2026, 10, 20, 22, 50, 0)

    cursor.execute("""
        INSERT INTO ActivityEvent (
            event_id,
            enrollment_id,
            learner_id,
            content_id,
            event_type,
            event_time_utc,
            received_at_utc,
            device_type,
            sync_status,
            idempotency_key,
            issue_type
        )
        VALUES (
            %s, %s, %s, %s, 'lesson_open',
            %s, %s, 'mobile', 'offline_synced', %s,
            'timezone_shift'
        )
    """, (
        event_id,
        enrollment_id,
        learner_id,
        content_id,
        event_time,
        received_time,
        event_id,
    ))

    print("Timezone-shift test case:", event_id)
    return event_id


def update_ground_truth(premature_id, timezone_id):
    """Update the last two scenario IDs in ground_truth.csv."""

    if not GROUND_TRUTH_PATH.exists():
        raise FileNotFoundError(
            f"Ground-truth file not found: {GROUND_TRUTH_PATH}"
        )

    with GROUND_TRUTH_PATH.open(
        "r",
        newline="",
        encoding="utf-8",
    ) as file:
        reader = csv.DictReader(file)
        rows = list(reader)
        fieldnames = reader.fieldnames

    if not fieldnames:
        raise ValueError("Ground-truth CSV has no header.")

    for row in rows:
        if row["anomaly_id"] == "ANOM-003":
            row["entity_id"] = premature_id

        elif row["anomaly_id"] == "ANOM-004":
            row["entity_id"] = timezone_id

    with GROUND_TRUTH_PATH.open(
        "w",
        newline="",
        encoding="utf-8",
    ) as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print("Ground-truth CSV updated.")


def main():
    connection = get_connection()
    cursor = connection.cursor()

    try:
        premature_id = inject_premature_completion(cursor)
        timezone_id = inject_timezone_shift(cursor)

        connection.commit()

        update_ground_truth(premature_id, timezone_id)

        print("\nRemaining anomaly scenarios completed.")

    except Exception:
        connection.rollback()
        raise

    finally:
        cursor.close()
        connection.close()


if __name__ == "__main__":
    main()
