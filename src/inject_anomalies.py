
import csv
from pathlib import Path

from src.db_connection import get_connection


GROUND_TRUTH_PATH = Path("data/ground_truth.csv")


def inject_duplicate_event(cursor):
    """Create a second event with an existing idempotency key."""

    cursor.execute("""
        SELECT
            event_id,
            enrollment_id,
            learner_id,
            content_id,
            event_type,
            event_time_utc,
            received_at_utc,
            device_type,
            sync_status,
            idempotency_key
        FROM ActivityEvent
        WHERE idempotency_key IS NOT NULL
        ORDER BY event_id
        LIMIT 1
    """)

    original = cursor.fetchone()

    if not original:
        raise RuntimeError(
            "No suitable activity event exists for duplication."
        )

    (
        original_id,
        enrollment_id,
        learner_id,
        content_id,
        event_type,
        event_time,
        received_at,
        device_type,
        sync_status,
        idempotency_key,
    ) = original

    anomaly_id = f"ANOM-DUP-{original_id}"

    cursor.execute(
        """
        SELECT event_id
        FROM ActivityEvent
        WHERE event_id = %s
        """,
        (anomaly_id,),
    )

    if cursor.fetchone():
        print("Duplicate-event anomaly already exists.")
        return anomaly_id

    cursor.execute(
        """
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
            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
        )
        """,
        (
            anomaly_id,
            enrollment_id,
            learner_id,
            content_id,
            event_type,
            event_time,
            received_at,
            device_type,
            sync_status,
            idempotency_key,
            "duplicate_event",
        ),
    )

    print("Inserted duplicate-event anomaly:", anomaly_id)
    return anomaly_id


def inject_unenrolled_activity(cursor):
    """Create an event for a learner not enrolled in that course."""

    cursor.execute("""
        SELECT
            l.learner_id,
            c.course_id,
            ci.content_id
        FROM Learner l
        CROSS JOIN Course c
        JOIN ContentItem ci
            ON ci.course_id = c.course_id
        WHERE NOT EXISTS (
            SELECT 1
            FROM Enrollment e
            WHERE e.learner_id = l.learner_id
              AND e.course_id = c.course_id
        )
        ORDER BY l.learner_id, c.course_id, ci.content_id
        LIMIT 1
    """)

    result = cursor.fetchone()

    if not result:
        raise RuntimeError(
            "Could not find a learner-course pair without enrollment."
        )

    learner_id, course_id, content_id = result
    event_id = "ANOM-UNENROLLED-001"

    cursor.execute(
        "SELECT event_id FROM ActivityEvent WHERE event_id = %s",
        (event_id,),
    )

    if cursor.fetchone():
        print("Unenrolled-activity anomaly already exists.")
        return event_id

    cursor.execute(
        """
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
            %s, NULL, %s, %s, %s, %s, %s, %s, %s, %s, %s
        )
        """,
        (
            event_id,
            learner_id,
            content_id,
            "lesson_open",
            "2026-10-20 10:00:00",
            "2026-10-20 10:00:00",
            "web",
            "online",
            event_id,
            "unenrolled_activity",
        ),
    )

    print(
        "Inserted unenrolled-activity anomaly:",
        event_id,
        "| learner:",
        learner_id,
        "| course:",
        course_id,
    )

    return event_id


def update_ground_truth(duplicate_id, unenrolled_id):
    """Update the first two rows of the separate ground-truth CSV."""

    rows = [
        {
            "anomaly_id": "ANOM-001",
            "anomaly_type": "duplicate_event",
            "entity_type": "ActivityEvent",
            "entity_id": duplicate_id,
            "expected_issue": "Repeated logical event inflates engagement",
            "severity": "high",
        },
        {
            "anomaly_id": "ANOM-002",
            "anomaly_type": "unenrolled_activity",
            "entity_type": "ActivityEvent",
            "entity_id": unenrolled_id,
            "expected_issue": (
                "Activity exists without a valid course enrollment"
            ),
            "severity": "high",
        },
        {
            "anomaly_id": "ANOM-003",
            "anomaly_type": "premature_completion",
            "entity_type": "CourseOutcome",
            "entity_id": "TO_BE_ASSIGNED",
            "expected_issue": (
                "Completion recorded before required assessment pass"
            ),
            "severity": "high",
        },
        {
            "anomaly_id": "ANOM-004",
            "anomaly_type": "timezone_shift",
            "entity_type": "ActivityEvent",
            "entity_id": "TO_BE_ASSIGNED",
            "expected_issue": (
                "UTC date differs from reporting-local date"
            ),
            "severity": "medium",
        },
    ]

    GROUND_TRUTH_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with GROUND_TRUTH_PATH.open(
        "w",
        newline="",
        encoding="utf-8",
    ) as file:
        writer = csv.DictWriter(
            file,
            fieldnames=[
                "anomaly_id",
                "anomaly_type",
                "entity_type",
                "entity_id",
                "expected_issue",
                "severity",
            ],
        )
        writer.writeheader()
        writer.writerows(rows)

    print("Ground-truth file updated:", GROUND_TRUTH_PATH)


def main():
    connection = get_connection()
    cursor = connection.cursor()

    try:
        duplicate_id = inject_duplicate_event(cursor)
        unenrolled_id = inject_unenrolled_activity(cursor)

        connection.commit()

        update_ground_truth(
            duplicate_id,
            unenrolled_id,
        )

        print("\nFirst two anomaly scenarios completed.")

    except Exception:
        connection.rollback()
        raise

    finally:
        cursor.close()
        connection.close()


if __name__ == "__main__":
    main()
