
import random
from datetime import date, datetime, timedelta

from src.config import (
    SEED,
    NUM_LEARNERS,
    NUM_COURSES,
    NUM_ENROLLMENTS,
)
from src.db_connection import get_connection


STAGING_DATABASE = "learnguard_staging"
BATCH_SIZE = 5_000


def learner_id(number):
    return f"LRN-{number:06d}"


def course_id(number):
    return f"CRS-{number:06d}"


def enrollment_id(learner, course):
    return f"ENR-{learner}-{course}"


def insert_in_batches(cursor, sql, rows):
    """Insert records in manageable batches."""
    for start in range(0, len(rows), BATCH_SIZE):
        cursor.executemany(
            sql,
            rows[start:start + BATCH_SIZE],
        )


def generate_learners(count, rng):
    """Generate deterministic synthetic learner records."""
    statuses = [
        "active",
        "active",
        "active",
        "inactive",
        "suspended",
    ]
    devices = ["web", "mobile", "tablet"]
    rows = []

    for number in range(1, count + 1):
        registered = date(2025, 1, 1) + timedelta(
            days=rng.randint(0, 650)
        )

        rows.append((
            learner_id(number),
            registered,
            rng.choice(statuses),
            rng.choice(devices),
            datetime.combine(
                registered,
                datetime.min.time(),
            ),
        ))

    return rows


def generate_courses(count, rng):
    """Generate deterministic synthetic course records."""
    categories = [
        "Programming",
        "Data Analytics",
        "Databases",
        "AI",
    ]
    difficulties = [
        "beginner",
        "intermediate",
        "advanced",
    ]
    rows = []

    for number in range(1, count + 1):
        category = rng.choice(categories)

        rows.append((
            course_id(number),
            f"{category} Course {number:03d}",
            category,
            rng.choice(difficulties),
            "published",
            datetime(2026, 1, 1),
        ))

    return rows


def generate_enrollments(
    learner_count,
    course_count,
    enrollment_count,
    learner_rows,
    rng,
):
    """
    Generate unique learner/course pairs.

    Sample integer indexes instead of building a list containing
    every possible learner/course combination. This reduces
    peak memory use for the full dataset.
    """
    if learner_count < 1 or course_count < 1:
        raise ValueError(
            "Learner and course counts must both be positive."
        )

    if enrollment_count < 0:
        raise ValueError(
            "Enrollment count cannot be negative."
        )

    maximum_pairs = learner_count * course_count

    if enrollment_count > maximum_pairs:
        raise ValueError(
            f"Requested {enrollment_count:,} enrollments, but only "
            f"{maximum_pairs:,} unique learner/course pairs are possible."
        )

    registration_dates = {
        row[0]: row[1]
        for row in learner_rows
    }

    # Each integer identifies one unique learner/course pair.
    selected_indexes = rng.sample(
        range(maximum_pairs),
        enrollment_count,
    )

    rows = []

    for pair_index in selected_indexes:
        learner_number = pair_index // course_count + 1
        course_number = pair_index % course_count + 1

        learner = learner_id(learner_number)
        course = course_id(course_number)

        registration_date = registration_dates[learner]
        earliest_date = max(
            date(2026, 1, 1),
            registration_date,
        )

        enrolled_date = earliest_date + timedelta(
            days=rng.randint(0, 270)
        )

        enrolled_at = datetime.combine(
            enrolled_date,
            datetime.min.time(),
        )

        rows.append((
            enrollment_id(learner, course),
            learner,
            course,
            enrolled_at,
            "active",
            enrolled_at.strftime("%Y-%m"),
        ))

    return rows


def main():
    rng = random.Random(SEED)
    connection = None
    cursor = None

    try:
        # Safety: never use the original database.
        connection = get_connection(
            database=STAGING_DATABASE
        )

        cursor = connection.cursor()

        cursor.execute("SELECT DATABASE()")
        active_database = cursor.fetchone()[0]

        if active_database != STAGING_DATABASE:
            raise RuntimeError(
                "Database safety check failed. Expected "
                f"{STAGING_DATABASE}, got {active_database!r}."
            )

        print("LEARNGUARD MASTER DATA GENERATOR")
        print("=" * 55)
        print(f"Database: {active_database}")
        print(f"Seed: {SEED}")
        print(f"Target learners: {NUM_LEARNERS:,}")
        print(f"Target courses: {NUM_COURSES:,}")
        print(f"Target enrollments: {NUM_ENROLLMENTS:,}")

        if NUM_ENROLLMENTS > NUM_LEARNERS * NUM_COURSES:
            raise ValueError(
                "The enrollment target exceeds the number of "
                "unique learner/course combinations."
            )

        learners = generate_learners(
            NUM_LEARNERS,
            rng,
        )

        courses = generate_courses(
            NUM_COURSES,
            rng,
        )

        enrollments = generate_enrollments(
            NUM_LEARNERS,
            NUM_COURSES,
            NUM_ENROLLMENTS,
            learners,
            rng,
        )

        learner_sql = """
            INSERT INTO Learner (
                learner_id,
                registration_date,
                learner_status,
                preferred_device,
                created_at
            )
            VALUES (%s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                registration_date = VALUES(registration_date),
                learner_status = VALUES(learner_status),
                preferred_device = VALUES(preferred_device),
                created_at = VALUES(created_at)
        """

        course_sql = """
            INSERT INTO Course (
                course_id,
                course_name,
                category,
                difficulty,
                course_status,
                created_at
            )
            VALUES (%s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                course_name = VALUES(course_name),
                category = VALUES(category),
                difficulty = VALUES(difficulty),
                course_status = VALUES(course_status),
                created_at = VALUES(created_at)
        """

        enrollment_sql = """
            INSERT INTO Enrollment (
                enrollment_id,
                learner_id,
                course_id,
                enrolled_at,
                enrollment_status,
                cohort_label
            )
            VALUES (%s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                learner_id = VALUES(learner_id),
                course_id = VALUES(course_id),
                enrolled_at = VALUES(enrolled_at),
                enrollment_status = VALUES(enrollment_status),
                cohort_label = VALUES(cohort_label)
        """

        print("\nWriting learners...")
        insert_in_batches(
            cursor,
            learner_sql,
            learners,
        )

        print("Writing courses...")
        insert_in_batches(
            cursor,
            course_sql,
            courses,
        )

        print("Writing enrollments...")
        insert_in_batches(
            cursor,
            enrollment_sql,
            enrollments,
        )

        connection.commit()

        print("\nMASTER DATA GENERATION COMPLETED")
        print("=" * 55)
        print(f"Learners generated: {len(learners):,}")
        print(f"Courses generated: {len(courses):,}")
        print(f"Enrollments generated: {len(enrollments):,}")
        print(f"Database: {STAGING_DATABASE}")
        print(f"Seed: {SEED}")
        print("\nExisting matching IDs are updated rather than duplicated.")
        print(
            "This script does not generate activity events, content, "
            "assessments, attempts, cohorts, or outcomes."
        )
        print(
            "It does not remove stale rows. A controlled full rebuild "
            "is required before changing dataset sizes."
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
