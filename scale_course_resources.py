
from datetime import datetime
from src.db_connection import get_connection

DB = "learnguard_staging"
EXPECTED_COURSES = 500


def main():
    conn = get_connection(database=DB)
    cur = conn.cursor()

    try:
        cur.execute("SELECT DATABASE()")
        active_db = cur.fetchone()[0]

        if active_db != DB:
            raise RuntimeError("Wrong database. Stopping.")

        cur.execute("SELECT course_id FROM Course ORDER BY course_id")
        courses = [row[0] for row in cur.fetchall()]

        if len(courses) != EXPECTED_COURSES:
            raise RuntimeError(
                f"Expected {EXPECTED_COURSES} courses, found {len(courses)}"
            )

        cur.execute("SELECT content_id, course_id, sequence_no FROM ContentItem")
        content_rows = cur.fetchall()

        content_by_course = {}
        for content_id, course_id, sequence in content_rows:
            content_by_course.setdefault(course_id, {})[sequence] = content_id

        cur.execute("SELECT course_id FROM Assessment")
        assessment_courses = {row[0] for row in cur.fetchall()}

        cur.execute("SELECT course_id FROM CompletionRule")
        rule_courses = {row[0] for row in cur.fetchall()}

        content_added = 0
        assessments_added = 0
        rules_added = 0

        print("Connected database:", active_db)
        print("Courses:", len(courses))
        print("Adding only missing course resources...")

        # Four content items per course.
        for course_id in courses:
            existing = content_by_course.get(course_id, {})

            module_id = f"MOD-{course_id}"

            content_items = [
                (module_id, None, "module", 1, None),
                (f"VID-{course_id}", module_id, "video", 2, 20),
                (f"REA-{course_id}", module_id, "reading", 3, 15),
                (f"EXE-{course_id}", module_id, "exercise", 4, 15),
            ]

            for content_id, parent_id, content_type, sequence, duration in content_items:
                if sequence in existing:
                    continue

                cur.execute("""
                    INSERT INTO ContentItem
                    (content_id, course_id, parent_content_id, title,
                     content_type, sequence_no, duration_minutes)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, (
                    content_id,
                    course_id,
                    parent_id,
                    f"{content_type.title()} for {course_id}",
                    content_type,
                    sequence,
                    duration
                ))

                content_added += 1
                existing[sequence] = content_id

        # One assessment per course, preserving existing assessments.
        for course_id in courses:
            if course_id in assessment_courses:
                continue

            number = int(course_id.split("-")[1])
            assessment_id = f"ASM-2026-{number:06d}"

            cur.execute("""
                INSERT INTO Assessment
                (assessment_id, course_id, assessment_name, passing_score,
                 max_score, available_from, available_until)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (
                assessment_id,
                course_id,
                f"Final Assessment - {course_id}",
                60.00,
                100.00,
                datetime(2026, 1, 1),
                datetime(2027, 1, 1)
            ))

            assessments_added += 1

        # One completion rule per course.
        for course_id in courses:
            if course_id in rule_courses:
                continue

            number = int(course_id.split("-")[1])
            rule_id = f"RULE-{number:06d}"

            cur.execute("""
                INSERT INTO CompletionRule
                (rule_id, course_id, effective_from, effective_until,
                 min_content_completion_pct, require_assessment_pass,
                 rule_version)
                VALUES (%s, %s, %s, NULL, %s, %s, %s)
            """, (
                rule_id,
                course_id,
                datetime(2026, 1, 1),
                80.00,
                1,
                1
            ))

            rules_added += 1

        # Verify expected totals before commit.
        expected_counts = {
            "ContentItem": 2000,
            "Assessment": 500,
            "CompletionRule": 500
        }

        for table, expected in expected_counts.items():
            cur.execute(f"SELECT COUNT(*) FROM `{table}`")
            actual = cur.fetchone()[0]
            print(f"{table}: {actual:,} / {expected:,}")

            if actual != expected:
                raise RuntimeError(
                    f"{table} count mismatch. Transaction will roll back."
                )

        conn.commit()

        print("\nSUCCESS: Course resources scaled.")
        print("New content items:", content_added)
        print("New assessments:", assessments_added)
        print("New completion rules:", rules_added)
        print("Existing records preserved.")

    except Exception:
        conn.rollback()
        print("ERROR: Transaction rolled back.")
        raise

    finally:
        cur.close()
        conn.close()


if __name__ == "__main__":
    main()
