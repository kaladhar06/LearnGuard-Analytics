
from src.config import (
    DATASET_MODE,
    NUM_LEARNERS,
    NUM_COURSES,
    NUM_ENROLLMENTS,
    NUM_EVENTS,
)
from src.db_connection import get_connection


EXPECTED_TABLES = [
    "Learner",
    "Course",
    "Enrollment",
    "ContentItem",
    "ActivityEvent",
    "Assessment",
    "Attempt",
    "CompletionRule",
    "CourseOutcome",
]


def main():
    connection = None
    cursor = None

    try:
        connection = get_connection(database="learnguard_staging")
        cursor = connection.cursor()

        print("LEARNGUARD ANALYTICS — PREFLIGHT CHECK")
        print("=" * 55)
        print(f"Dataset mode: {DATASET_MODE}")
        print(f"Configured learners: {NUM_LEARNERS:,}")
        print(f"Configured courses: {NUM_COURSES:,}")
        print(f"Configured enrollments: {NUM_ENROLLMENTS:,}")
        print(f"Configured activity events: {NUM_EVENTS:,}")

        cursor.execute("SELECT DATABASE()")
        database_name = cursor.fetchone()[0]
        print(f"Connected database: {database_name}")

        if database_name != "learnguard_staging":
            raise RuntimeError(
                "Safety check failed: unexpected database."
            )

        print("\nCurrent database row counts:")

        for table in EXPECTED_TABLES:
            cursor.execute(f"SELECT COUNT(*) FROM `{table}`")
            count = cursor.fetchone()[0]
            print(f"{table:<18} {count:>12,}")

        cursor.execute("""
            SELECT COUNT(*)
            FROM ActivityEvent
            WHERE issue_type IS NOT NULL
        """)
        flagged_events = cursor.fetchone()[0]

        cursor.execute("""
            SELECT COUNT(*)
            FROM CourseOutcome
            WHERE outcome_id LIKE 'ANOM-%'
        """)
        flagged_outcomes = cursor.fetchone()[0]

        print(f"\nFlagged activity events: {flagged_events}")
        print(f"Flagged outcome records: {flagged_outcomes}")

        print("\nPREFLIGHT PASSED: database connection and table checks succeeded.")
        print(
            "Note: this check does not prove the database is safe to reset. "
            "The current dataset must still be backed up and regeneration "
            "must be explicitly controlled."
        )

    except Exception as error:
        print(f"\nPREFLIGHT FAILED: {error}")
        raise

    finally:
        if cursor is not None:
            cursor.close()

        if connection is not None:
            connection.close()


if __name__ == "__main__":
    main()
