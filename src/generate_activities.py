
import csv
import random
from collections import Counter
from datetime import timedelta
from pathlib import Path

from src.config import NUM_EVENTS, SEED
from src.db_connection import get_connection


STAGING_DATABASE = "learnguard_staging"
OUTPUT_FILE = Path("data/generated_activity_preview.csv")

EVENT_TYPES = [
    "lesson_open",
    "video_progress",
    "content_complete",
    "assessment_submit",
]

DEVICES = ["web", "mobile", "tablet"]


def main():
    connection = None
    cursor = None

    try:
        if NUM_EVENTS != 2000:
            raise ValueError(
                "This preview script currently expects the test target "
                "to be exactly 2,000 events."
            )

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
            SELECT
                e.enrollment_id,
                e.learner_id,
                e.course_id,
                e.enrolled_at
            FROM Enrollment e
            ORDER BY e.enrollment_id
        """)
        enrollments = cursor.fetchall()

        if not enrollments:
            raise RuntimeError("No enrollments found in staging.")

        cursor.execute("""
            SELECT content_id, course_id, content_type
            FROM ContentItem
            ORDER BY course_id, sequence_no
        """)
        content_rows = cursor.fetchall()

        content_by_course = {}
        for item in content_rows:
            content_by_course.setdefault(
                item["course_id"], []
            ).append(item)

        for enrollment in enrollments:
            if not content_by_course.get(enrollment["course_id"]):
                raise RuntimeError(
                    "Missing content for course "
                    f"{enrollment['course_id']}"
                )

        # Keep approximately 10% of enrollments inactive in this
        # baseline preview. The selection is reproducible by seed.
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

        if len(active_enrollments) * 7 > NUM_EVENTS:
            raise RuntimeError(
                "Too many active enrollments for the configured target."
            )

        # Distribute exactly NUM_EVENTS across active enrollments.
        # Every active enrollment receives at least seven events.
        base_count, remainder = divmod(
            NUM_EVENTS, len(active_enrollments)
        )

        event_counts = {
            row["enrollment_id"]: base_count
            for row in active_enrollments
        }

        for row in active_enrollments[:remainder]:
            event_counts[row["enrollment_id"]] += 1

        records = []
        sequence_by_enrollment = Counter()

        for enrollment in active_enrollments:
            enrollment_id = enrollment["enrollment_id"]
            course_content = content_by_course[
                enrollment["course_id"]
            ]

            for _ in range(event_counts[enrollment_id]):
                sequence_by_enrollment[enrollment_id] += 1
                sequence = sequence_by_enrollment[enrollment_id]

                event_type = rng.choice(EVENT_TYPES)

                # Assessment submissions do not require a content ID.
                if event_type == "assessment_submit":
                    content_id = None
                else:
                    matching_content = [
                        item for item in course_content
                        if (
                            event_type != "video_progress"
                            or item["content_type"] == "video"
                        )
                    ]

                    if not matching_content:
                        raise RuntimeError(
                            f"No suitable content for {event_type}"
                        )

                    content_id = rng.choice(
                        matching_content
                    )["content_id"]

                event_time = enrollment["enrolled_at"] + timedelta(
                    days=rng.randint(0, 120),
                    hours=rng.randint(0, 23),
                    minutes=rng.randint(0, 59),
                )

                # Most events arrive immediately. Some are delayed
                # to simulate offline synchronization.
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

                records.append({
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

        if len(records) != NUM_EVENTS:
            raise RuntimeError(
                f"Expected {NUM_EVENTS} records; generated {len(records)}."
            )

        # Validate the preview before writing it.
        event_ids = [row["event_id"] for row in records]

        if len(event_ids) != len(set(event_ids)):
            raise RuntimeError("Duplicate generated event IDs detected.")

        if any(
            row["received_at_utc"] < row["event_time_utc"]
            for row in records
        ):
            raise RuntimeError("An event has an invalid received timestamp.")

        OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

        fieldnames = [
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

        with OUTPUT_FILE.open(
            "w", newline="", encoding="utf-8"
        ) as csv_file:
            writer = csv.DictWriter(
                csv_file,
                fieldnames=fieldnames,
            )
            writer.writeheader()
            writer.writerows(records)

        event_type_counts = Counter(
            row["event_type"] for row in records
        )

        print("LEARNGUARD — DETERMINISTIC EVENT PREVIEW")
        print("=" * 46)
        print(f"Database inspected:       {active_database}")
        print(f"Configured target:        {NUM_EVENTS:,}")
        print(f"Generated baseline rows:  {len(records):,}")
        print(f"Active enrollments:       {len(active_enrollments):,}")
        print(f"Inactive enrollments:     {len(inactive_ids):,}")
        print(f"Unique event IDs:         {len(set(event_ids)):,}")
        print("\nEvent type distribution:")

        for event_type in EVENT_TYPES:
            print(
                f"  {event_type:<20} "
                f"{event_type_counts[event_type]:,}"
            )

        print(f"\nPreview saved to: {OUTPUT_FILE}")
        print("DRY RUN ONLY: no database rows were changed.")
        print("Existing anomaly records remain untouched.")

    finally:
        if cursor is not None:
            cursor.close()

        if connection is not None:
            connection.close()


if __name__ == "__main__":
    main()
