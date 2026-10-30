
import random
from datetime import date, datetime, timedelta

from src.config import SEED, NUM_LEARNERS, NUM_COURSES, NUM_ENROLLMENTS
from src.db_connection import get_connection

DB = "learnguard_staging"
BATCH_SIZE = 5000


def insert_batches(cursor, sql, rows):
    for start in range(0, len(rows), BATCH_SIZE):
        cursor.executemany(sql, rows[start:start + BATCH_SIZE])


def main():
    rng = random.Random(SEED)
    conn = get_connection(database=DB)
    cursor = conn.cursor()

    try:
        cursor.execute("SELECT DATABASE()")
        active_db = cursor.fetchone()[0]
        print("Connected database:", active_db)

        if active_db != DB:
            raise RuntimeError("Wrong database. Stopping.")

        # Read existing records. Never update or delete them.
        cursor.execute("SELECT learner_id, registration_date FROM Learner")
        existing_learners = dict(cursor.fetchall())

        cursor.execute("SELECT course_id FROM Course")
        existing_courses = {row[0] for row in cursor.fetchall()}

        cursor.execute("SELECT learner_id, course_id FROM Enrollment")
        existing_pairs = set(cursor.fetchall())

        if len(existing_learners) > NUM_LEARNERS:
            raise RuntimeError("Existing learner count exceeds target.")
        if len(existing_courses) > NUM_COURSES:
            raise RuntimeError("Existing course count exceeds target.")
        if len(existing_pairs) > NUM_ENROLLMENTS:
            raise RuntimeError("Existing enrollment count exceeds target.")

        # Ensure existing enrollments fit the target ID ranges.
        for learner, course in existing_pairs:
            if learner not in {
                f"LRN-{i:06d}" for i in range(1, NUM_LEARNERS + 1)
            }:
                raise RuntimeError(f"Existing learner outside target range: {learner}")
            if course not in {
                f"CRS-{i:06d}" for i in range(1, NUM_COURSES + 1)
            }:
                raise RuntimeError(f"Existing course outside target range: {course}")

        print("\nExisting records:")
        print("Learners:", len(existing_learners))
        print("Courses:", len(existing_courses))
        print("Enrollments:", len(existing_pairs))

        # Add missing learners only.
        learner_rows = []
        for i in range(1, NUM_LEARNERS + 1):
            lid = f"LRN-{i:06d}"
            if lid in existing_learners:
                continue

            registered = date(2025, 1, 1) + timedelta(
                days=rng.randint(0, 650)
            )
            learner_rows.append((
                lid,
                registered,
                rng.choice(["active", "active", "active", "inactive", "suspended"]),
                rng.choice(["web", "mobile", "tablet"]),
                datetime.combine(registered, datetime.min.time())
            ))

        insert_batches(cursor, """
            INSERT INTO Learner
            (learner_id, registration_date, learner_status,
             preferred_device, created_at)
            VALUES (%s, %s, %s, %s, %s)
        """, learner_rows)

        # Build registration-date lookup for all target learners.
        cursor.execute("SELECT learner_id, registration_date FROM Learner")
        registration_dates = dict(cursor.fetchall())

        # Add missing courses only.
        course_rows = []
        categories = ["Programming", "Data Analytics", "Databases", "AI"]
        difficulties = ["beginner", "intermediate", "advanced"]

        for i in range(1, NUM_COURSES + 1):
            cid = f"CRS-{i:06d}"
            if cid in existing_courses:
                continue

            category = rng.choice(categories)
            course_rows.append((
                cid,
                f"{category} Course {i:03d}",
                category,
                rng.choice(difficulties),
                "published",
                datetime(2026, 1, 1)
            ))

        insert_batches(cursor, """
            INSERT INTO Course
            (course_id, course_name, category, difficulty,
             course_status, created_at)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, course_rows)

        # Generate only missing unique learner/course pairs.
        needed = NUM_ENROLLMENTS - len(existing_pairs)
        new_enrollments = []
        selected_pairs = set(existing_pairs)

        while len(new_enrollments) < needed:
            learner_num = rng.randint(1, NUM_LEARNERS)
            course_num = rng.randint(1, NUM_COURSES)

            learner = f"LRN-{learner_num:06d}"
            course = f"CRS-{course_num:06d}"
            pair = (learner, course)

            if pair in selected_pairs:
                continue

            selected_pairs.add(pair)

            reg_date = registration_dates[learner]
            earliest = max(date(2026, 1, 1), reg_date)
            enrolled_date = earliest + timedelta(days=rng.randint(0, 270))
            enrolled_at = datetime.combine(
                enrolled_date, datetime.min.time()
            )

            enrollment_id = f"ENR-{learner}-{course}"

            new_enrollments.append((
                enrollment_id,
                learner,
                course,
                enrolled_at,
                "active",
                enrolled_at.strftime("%Y-%m")
            ))

        insert_batches(cursor, """
            INSERT INTO Enrollment
            (enrollment_id, learner_id, course_id,
             enrolled_at, enrollment_status, cohort_label)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, new_enrollments)

        # Verify targets before committing.
        for table, target in [
            ("Learner", NUM_LEARNERS),
            ("Course", NUM_COURSES),
            ("Enrollment", NUM_ENROLLMENTS)
        ]:
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            actual = cursor.fetchone()[0]
            print(f"{table}: {actual:,} / {target:,}")

            if actual != target:
                raise RuntimeError(
                    f"{table} count does not match target. Rolling back."
                )

        conn.commit()
        print("\nSUCCESS: Master data scaled and committed.")
        print("Existing rows were preserved.")

    except Exception:
        conn.rollback()
        print("\nERROR: Changes rolled back.")
        raise

    finally:
        cursor.close()
        conn.close()


if __name__ == "__main__":
    main()
