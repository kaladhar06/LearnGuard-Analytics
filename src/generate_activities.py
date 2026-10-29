
import csv
import random
from collections import Counter
from datetime import timedelta
from pathlib import Path

from src.config import NUM_EVENTS, SEED
from src.db_connection import get_connection


STAGING_DATABASE = "learnguard_staging"
OUTPUT_FILE = Path("data/generated_activity_preview.csv")
BATCH_SIZE = 10_000

EVENT_TYPES = [
    "lesson_open",
    "video_progress",
    "content_complete",
    "assessment_submit",
]

DEVICES = ["web", "mobile", "tablet"]

FIELDNAMES = [
    "event_id",
    "enrollment_id",
    "content_id",
    "event_type",
    "event_time_utc",
    "received_at_utc",
    "device_type",
    "sync_status",
    "idempotency_key",
    "issue_type",
    "learner_id",
]


def write_batch(writer, batch):
    """Write a bounded batch and release its memory."""
    if batch:
        writer.writerows(batch)
        count = len(batch)
        batch.clear()
        return count
    return 0


def main():
    connection = None
    cursor = None

    try:
        rng = random.Random(SEED)

        connection = get_connection(database=STAGING_DATABASE)
        cursor = connection.cursor(dictionary=True)

        cursor.execute("SELECT DATABASE() AS db_name")
        active_database = cursor.fetchone()["db_name"]

        if active_database != STAGING_DATABASE:
            raise RuntimeError(
                f"Safety check failed: connected to {active_database}"
            )

        cursor.execute("""
            SELECT enrollment_id, learner_id, course_id, enrolled_at
            FROM Enrollment
            ORDER BY enrollment_id
        """)
        enrollments = cursor.fetchall()

        if not enrollments:
            raise RuntimeError("No enrollments found in staging.")

        cursor.execute("""
            SELECT content_id, course_id, content_type
            FROM ContentItem
            ORDER BY course_id, sequence_no
        """)

        content_by_course = {}
        for item in cursor.fetchall():
            content_by_course.setdefault(
                item["course_id"], []
            ).append(item)

        for enrollment in enrollments:
            if not content_by_course.get(enrollment["course_id"]):
                raise RuntimeError(
                    f"Missing content for course "
                    f"{enrollment['course_id']}"
                )

        inactive_count = min(
            len(enrollments) - 1,
            round(len(enrollments) * 0.10),
        )

        inactive_ids = {
            row["enrollment_id"]
            for row in rng.sample(enrollments, inactive_count)
        }

        active_enrollments = [
            row for row in enrollments
            if row["enrollment_id"] not in inactive_ids
        ]

        if not active_enrollments:
            raise RuntimeError("No active enrollments available.")

        base_count, remainder = divmod(
            NUM_EVENTS, len(active_enrollments)
        )

        event_counts = {
            row["enrollment_id"]: base_count
            for row in active_enrollments
        }

        for row in active_enrollments[:remainder]:
            event_counts[row["enrollment_id"]] += 1

        OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

        event_type_counts = Counter()
        total_written = 0
        batch = []

        with OUTPUT_FILE.open(
            "w", newline="", encoding="utf-8"
        ) as csv_file:
            writer = csv.DictWriter(
                csv_file,
                fieldnames=FIELDNAMES,
            )
            writer.writeheader()

            for enrollment in active_enrollments:
                enrollment_id = enrollment["enrollment_id"]
                course_content = content_by_course[
                    enrollment["course_id"]
                ]

                video_content = [
                    item for item in course_content
                    if item["content_type"] == "video"
                ]

                for sequence in range(
                    1, event_counts[enrollment_id] + 1
                ):
                    event_type = rng.choice(EVENT_TYPES)

                    if event_type == "assessment_submit":
                        content_id = None

                    elif event_type == "video_progress":
                        if video_content:
                            content_id = rng.choice(
                                video_content
                            )["content_id"]
                        else:
                            event_type = "lesson_open"
                            content_id = rng.choice(
                                course_content
                            )["content_id"]

                    else:
                        content_id = rng.choice(
                            course_content
                        )["content_id"]

                    event_time = enrollment["enrolled_at"] + timedelta(
                        days=rng.randint(0, 120),
                        hours=rng.randint(0, 23),
                        minutes=rng.randint(0, 59),
                    )

                    if rng.random() < 0.15:
                        delay_minutes = rng.randint(5, 480)
                        sync_status = "offline_synced"
                    else:
                        delay_minutes = 0
                        sync_status = "online"

                    received_at = event_time + timedelta(
                        minutes=delay_minutes
                    )

                    event_id = (
                        f"EVT-{enrollment_id}-{sequence:06d}"
                    )

                    batch.append({
                        "event_id": event_id,
                        "enrollment_id": enrollment_id,
                        "content_id": content_id,
                        "event_type": event_type,
                        "event_time_utc": event_time.strftime(
                            "%Y-%m-%d %H:%M:%S"
                        ),
                        "received_at_utc": received_at.strftime(
                            "%Y-%m-%d %H:%M:%S"
                        ),
                        "device_type": rng.choice(DEVICES),
                        "sync_status": sync_status,
                        "idempotency_key": event_id,
                        "issue_type": None,
                        "learner_id": enrollment["learner_id"],
                    })

                    event_type_counts[event_type] += 1

                    if len(batch) >= BATCH_SIZE:
                        total_written += write_batch(writer, batch)

                        if total_written % 100_000 == 0:
                            print(
                                f"Generated {total_written:,} events...",
                                flush=True,
                            )

            total_written += write_batch(writer, batch)

        if total_written != NUM_EVENTS:
            raise RuntimeError(
                f"Expected {NUM_EVENTS:,} events; "
                f"generated {total_written:,}."
            )

        print("\nLEARNGUARD ANALYTICS — EVENT GENERATION")
        print("=" * 48)
        print(f"Database inspected:       {active_database}")
        print(f"Configured target:        {NUM_EVENTS:,}")
        print(f"Generated baseline rows:  {total_written:,}")
        print(f"Active enrollments:       {len(active_enrollments):,}")
        print(f"Inactive enrollments:     {len(inactive_ids):,}")
        print("\nEvent type distribution:")

        for event_type in EVENT_TYPES:
            print(
                f"  {event_type:<20} "
                f"{event_type_counts[event_type]:,}"
            )

        print(f"\nCSV saved to: {OUTPUT_FILE}")
        print("DRY RUN ONLY: no database rows were changed.")

    finally:
        if cursor is not None:
            cursor.close()

        if connection is not None:
            connection.close()


if __name__ == "__main__":
    main()
