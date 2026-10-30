
import calendar
from src.db_connection import get_connection

DB = "learnguard_staging"

conn = get_connection(database=DB)
cur = conn.cursor()

try:
    cur.execute("SELECT DATABASE()")
    if cur.fetchone()[0] != DB:
        raise RuntimeError("Wrong database. Stopping.")

    # Find all enrollment months.
    cur.execute("""
        SELECT DISTINCT DATE_FORMAT(enrolled_at, '%Y-%m')
        FROM Enrollment
        ORDER BY 1
    """)
    months = [row[0] for row in cur.fetchall()]

    # Add missing monthly cohorts without updating existing cohorts.
    for month in months:
        year, month_number = map(int, month.split("-"))
        last_day = calendar.monthrange(year, month_number)[1]
        cohort_id = f"COH-{month}"
        cohort_name = (
            f"Enrollment Cohort "
            f"{calendar.month_name[month_number]} {year}"
        )

        cur.execute("""
            INSERT IGNORE INTO Cohort
            (cohort_id, cohort_name, cohort_type, start_date, end_date)
            VALUES (%s, %s, 'enrollment_month', %s, %s)
        """, (
            cohort_id,
            cohort_name,
            f"{month}-01",
            f"{month}-{last_day:02d}"
        ))

    # Assign only enrollments that currently have no cohort.
    cur.execute("""
        INSERT IGNORE INTO EnrollmentCohort
        (enrollment_id, cohort_id, assigned_at)
        SELECT
            e.enrollment_id,
            CONCAT('COH-', DATE_FORMAT(e.enrolled_at, '%Y-%m')),
            e.enrolled_at
        FROM Enrollment e
        LEFT JOIN EnrollmentCohort ec
            ON ec.enrollment_id = e.enrollment_id
        WHERE ec.enrollment_id IS NULL
    """)

    cur.execute("""
        SELECT COUNT(*)
        FROM Enrollment e
        LEFT JOIN EnrollmentCohort ec
            ON ec.enrollment_id = e.enrollment_id
        WHERE ec.enrollment_id IS NULL
    """)
    missing = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM Cohort")
    cohort_count = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM EnrollmentCohort")
    mapping_count = cur.fetchone()[0]

    print("Cohorts:", cohort_count)
    print("Enrollment cohort mappings:", mapping_count)
    print("Enrollments without cohort:", missing)

    if missing != 0:
        raise RuntimeError("Some enrollments still lack cohort assignments.")

    conn.commit()
    print("\nSUCCESS: Cohort assignments completed.")

except Exception:
    conn.rollback()
    raise

finally:
    cur.close()
    conn.close()
