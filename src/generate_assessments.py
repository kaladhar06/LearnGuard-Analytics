
from datetime import datetime
from src.db_connection import get_connection

STAGING_DATABASE = "learnguard_staging"


def main():
    connection = None
    cursor = None

    try:
        connection = get_connection(database=STAGING_DATABASE)
        cursor = connection.cursor()

        cursor.execute("SELECT DATABASE()")
        active_database = cursor.fetchone()[0]

        if active_database != STAGING_DATABASE:
            raise RuntimeError(
                f"Safety check failed: connected to {active_database}"
            )

        cursor.execute("SELECT COUNT(*) FROM Assessment")
        assessment_count = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM CompletionRule")
        rule_count = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM Attempt")
        attempt_count = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM CourseOutcome")
        outcome_count = cursor.fetchone()[0]

        print("LEARNGUARD ASSESSMENT SAFETY CHECK")
        print("=" * 42)
        print(f"Database:          {active_database}")
        print(f"Assessments:       {assessment_count}")
        print(f"Completion rules:  {rule_count}")
        print(f"Attempts:          {attempt_count}")
        print(f"Course outcomes:   {outcome_count}")
        print()
        print("DRY RUN ONLY: no database changes made.")
        print("Existing assessment, attempt, and outcome records")
        print("were preserved. A controlled rebuild is required.")

        # The existing assessment/outcome generator uses INSERT IGNORE.
        # Rebuilding safely requires a separate, explicitly reviewed
        # transaction that preserves the injected anomaly records.
        print(
            "\nNext: rebuild assessments and outcomes in a dedicated "
            "staging workflow after the activity baseline is approved."
        )

    except Exception:
        if connection is not None:
            connection.rollback()
        raise

    finally:
        if cursor is not None:
            cursor.close()
        if connection is not None:
            connection.close()


if __name__ == "__main__":
    main()
