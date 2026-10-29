
from src.db_connection import get_connection

STAGING_DATABASE = "learnguard_staging"


CHECKS = {
    "Enrollments with missing learners": """
        SELECT COUNT(*)
        FROM Enrollment e
        LEFT JOIN Learner l
            ON l.learner_id = e.learner_id
        WHERE l.learner_id IS NULL
    """,

    "Enrollments with missing courses": """
        SELECT COUNT(*)
        FROM Enrollment e
        LEFT JOIN Course c
            ON c.course_id = e.course_id
        WHERE c.course_id IS NULL
    """,

    "Events with missing enrollment references": """
        SELECT COUNT(*)
        FROM ActivityEvent ae
        LEFT JOIN Enrollment e
            ON e.enrollment_id = ae.enrollment_id
        WHERE ae.enrollment_id IS NOT NULL
          AND e.enrollment_id IS NULL
    """,

    "Events with mismatched learner and enrollment": """
        SELECT COUNT(*)
        FROM ActivityEvent ae
        JOIN Enrollment e
            ON e.enrollment_id = ae.enrollment_id
        WHERE ae.learner_id IS NOT NULL
          AND ae.learner_id <> e.learner_id
    """,

    "Events referencing content from another course": """
        SELECT COUNT(*)
        FROM ActivityEvent ae
        JOIN ContentItem ci
            ON ci.content_id = ae.content_id
        JOIN Enrollment e
            ON e.enrollment_id = ae.enrollment_id
        WHERE ci.course_id <> e.course_id
    """,

    "Attempts referencing assessments from another course": """
        SELECT COUNT(*)
        FROM Attempt a
        JOIN Enrollment e
            ON e.enrollment_id = a.enrollment_id
        JOIN Assessment asm
            ON asm.assessment_id = a.assessment_id
        WHERE e.course_id <> asm.course_id
    """,

    "Outcomes referencing rules from another course": """
        SELECT COUNT(*)
        FROM CourseOutcome co
        JOIN Enrollment e
            ON e.enrollment_id = co.enrollment_id
        JOIN CompletionRule cr
            ON cr.rule_id = co.rule_id
        WHERE e.course_id <> cr.course_id
    """,

    "Invalid assessment date ranges": """
        SELECT COUNT(*)
        FROM Assessment
        WHERE available_until < available_from
    """,

    "Invalid enrollment date ordering": """
        SELECT COUNT(*)
        FROM Enrollment e
        JOIN Learner l
            ON l.learner_id = e.learner_id
        WHERE DATE(e.enrolled_at) < l.registration_date
    """,

    "Repeated event idempotency keys": """
        SELECT COUNT(*)
        FROM (
            SELECT idempotency_key
            FROM ActivityEvent
            WHERE idempotency_key IS NOT NULL
            GROUP BY idempotency_key
            HAVING COUNT(*) > 1
        ) AS duplicate_keys
    """,

    "Activity from unenrolled learners": """
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
}


def main():
    connection = None
    cursor = None
    failed_checks = 0

    print("LEARNGUARD ANALYTICS - DATA VALIDATION")
    print("=" * 55)

    try:
        connection = get_connection(
            database=STAGING_DATABASE
        )
        cursor = connection.cursor()

        cursor.execute("SELECT DATABASE()")
        active_database = cursor.fetchone()[0]

        if active_database != STAGING_DATABASE:
            raise RuntimeError(
                f"Safety check failed: connected to {active_database}"
            )

        print(f"Database: {active_database}")
        print()

        for check_name, query in CHECKS.items():
            cursor.execute(query)
            result = cursor.fetchone()
            issue_count = result[0]

            if issue_count == 0:
                status = "PASS"
            else:
                status = "REVIEW"
                failed_checks += 1

            print(
                f"{status:<8} | {check_name}: {issue_count}"
            )

        print("=" * 55)

        if failed_checks:
            print(
                f"Checks requiring review: {failed_checks}"
            )
        else:
            print("All implemented validation checks passed.")

    except Exception as error:
        print("VALIDATION ERROR:", error)
        raise

    finally:
        if cursor is not None:
            cursor.close()

        if connection is not None:
            connection.close()


if __name__ == "__main__":
    main()