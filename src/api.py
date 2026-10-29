
from datetime import date
from typing import Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from src.db_connection import get_connection

app = FastAPI(
    title="LearnGuard Analytics API",
    description="Learning analytics, learner mastery, recommendations and learning paths.",
    version="1.0.0",
)

STAGING_DATABASE = "learnguard_staging"


def fetch_all(query: str, params: tuple = ()):
    """Read data exclusively from the staging database."""
    connection = get_connection(database=STAGING_DATABASE)
    try:
        cursor = connection.cursor(dictionary=True)
        cursor.execute(query, params)
        return cursor.fetchall()
    finally:
        connection.close()


def execute_write(query: str, params: tuple = ()):
    """Write only to the staging database."""
    connection = get_connection(database=STAGING_DATABASE)
    try:
        cursor = connection.cursor()
        cursor.execute(query, params)
        connection.commit()
        return cursor.lastrowid
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


class LearningPathRequest(BaseModel):
    course_id: str = Field(min_length=1, max_length=13)
    goal: str = Field(default="Complete course", max_length=200)
    target_date: Optional[date] = None


@app.get("/")
def root():
    return {
        "project": "LearnGuard Analytics",
        "status": "running",
        "database": STAGING_DATABASE,
        "docs": "/docs",
    }


@app.get("/health")
def health():
    try:
        rows = fetch_all("SELECT DATABASE() AS database_name")
        return {
            "status": "healthy",
            "database": rows[0]["database_name"],
        }
    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail=f"Database unavailable: {type(exc).__name__}",
        )


@app.get("/learners/{learner_id}/mastery")
def learner_mastery(learner_id: str):
    learners = fetch_all(
        """
        SELECT learner_id, learner_status
        FROM Learner
        WHERE learner_id = %s
        """,
        (learner_id,),
    )
    if not learners:
        raise HTTPException(status_code=404, detail="Learner not found")

    rows = fetch_all(
        """
        SELECT
            e.course_id,
            c.course_name,
            COUNT(DISTINCT ce.content_id) AS total_content,
            COUNT(DISTINCT CASE
                WHEN ce.event_type = 'content_complete'
                THEN ce.content_id
            END) AS completed_content,
            MAX(CASE
                WHEN o.outcome_status = 'completed' THEN 1
                ELSE 0
            END) AS course_completed
        FROM Enrollment e
        JOIN Course c ON c.course_id = e.course_id
        LEFT JOIN ContentItem ci ON ci.course_id = e.course_id
        LEFT JOIN ActivityEvent ce
            ON ce.enrollment_id = e.enrollment_id
            AND ce.content_id = ci.content_id
            AND ce.issue_type IS NULL
        LEFT JOIN CourseOutcome o ON o.enrollment_id = e.enrollment_id
        WHERE e.learner_id = %s
        GROUP BY e.enrollment_id, e.course_id, c.course_name
        ORDER BY e.course_id
        """,
        (learner_id,),
    )

    courses = []
    for row in rows:
        total = row["total_content"] or 0
        completed = row["completed_content"] or 0
        courses.append({
            "course_id": row["course_id"],
            "course_name": row["course_name"],
            "total_content": total,
            "completed_content": completed,
            "mastery_percentage": round(completed / total * 100, 2)
                if total else 0,
            "course_completed": bool(row["course_completed"]),
        })

    return {
        "learner_id": learner_id,
        "learner_status": learners[0]["learner_status"],
        "courses": courses,
    }


@app.get("/learners/{learner_id}/recommendations")
def recommendations(learner_id: str):
    learners = fetch_all(
        "SELECT learner_id FROM Learner WHERE learner_id = %s",
        (learner_id,),
    )
    if not learners:
        raise HTTPException(status_code=404, detail="Learner not found")

    rows = fetch_all(
        """
        SELECT
            e.course_id,
            c.course_name,
            COUNT(DISTINCT ci.content_id) AS total_content,
            COUNT(DISTINCT CASE
                WHEN a.event_type = 'content_complete'
                THEN a.content_id
            END) AS completed_content,
            MAX(CASE WHEN o.outcome_status = 'completed'
                THEN 1 ELSE 0 END) AS is_completed
        FROM Enrollment e
        JOIN Course c ON c.course_id = e.course_id
        LEFT JOIN ContentItem ci ON ci.course_id = e.course_id
        LEFT JOIN ActivityEvent a
            ON a.enrollment_id = e.enrollment_id
            AND a.content_id = ci.content_id
            AND a.issue_type IS NULL
        LEFT JOIN CourseOutcome o ON o.enrollment_id = e.enrollment_id
        WHERE e.learner_id = %s
          AND e.enrollment_status = 'active'
        GROUP BY e.enrollment_id, e.course_id, c.course_name
        HAVING is_completed = 0
        ORDER BY
            CASE WHEN total_content = 0 THEN 0
                 ELSE completed_content / total_content END ASC
        LIMIT 5
        """,
        (learner_id,),
    )

    return {
        "learner_id": learner_id,
        "recommendations": [
            {
                "course_id": row["course_id"],
                "course_name": row["course_name"],
                "reason": "Continue an active course with unfinished content.",
                "completed_content": row["completed_content"] or 0,
                "total_content": row["total_content"] or 0,
            }
            for row in rows
        ],
    }


@app.post("/learners/{learner_id}/learning-paths")
def create_learning_path(learner_id: str, request: LearningPathRequest):
    learner = fetch_all(
        "SELECT learner_id FROM Learner WHERE learner_id = %s",
        (learner_id,),
    )
    if not learner:
        raise HTTPException(status_code=404, detail="Learner not found")

    course = fetch_all(
        "SELECT course_id, course_name FROM Course WHERE course_id = %s",
        (request.course_id,),
    )
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    enrollment = fetch_all(
        """
        SELECT enrollment_id
        FROM Enrollment
        WHERE learner_id = %s AND course_id = %s
        """,
        (learner_id, request.course_id),
    )
    if not enrollment:
        raise HTTPException(
            status_code=400,
            detail="Learner must be enrolled in the requested course.",
        )

    return {
        "learner_id": learner_id,
        "course_id": request.course_id,
        "course_name": course[0]["course_name"],
        "goal": request.goal,
        "target_date": (
            request.target_date.isoformat()
            if request.target_date else None
        ),
        "learning_path": [
            "Review unfinished course content",
            "Complete required learning activities",
            "Take the required assessment",
            "Verify completion against course rules",
        ],
        "status": "generated",
        "note": "This endpoint generates a learning path response; it does not persist a path record.",
    }


@app.get(
    "/learners/{learner_id}/courses/{course_id}/learning-content"
)
def learning_content(learner_id: str, course_id: str):
    enrollment = fetch_all(
        """
        SELECT enrollment_id
        FROM Enrollment
        WHERE learner_id = %s AND course_id = %s
        """,
        (learner_id, course_id),
    )
    if not enrollment:
        raise HTTPException(
            status_code=404,
            detail="No enrollment found for this learner and course",
        )

    content = fetch_all(
        """
        SELECT content_id, title, content_type, sequence_no,
               duration_minutes
        FROM ContentItem
        WHERE course_id = %s
        ORDER BY sequence_no
        """,
        (course_id,),
    )

    return {
        "learner_id": learner_id,
        "course_id": course_id,
        "content_count": len(content),
        "content": content,
    }
