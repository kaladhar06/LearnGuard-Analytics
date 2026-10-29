# LearnGuard Analytics — Data Dictionary

## Overview

LearnGuard Analytics is a synthetic learning-platform analytics dataset. It supports analysis of learner participation, content usage, assessment progress, completion outcomes, and data-quality anomalies.

## Tables

| Table | Purpose | Key fields |
|---|---|---|
| Learner | Learner profiles | learner_id, registration_date, learner_status |
| Course | Course catalogue | course_id, category, difficulty, course_status |
| Enrollment | Learner-course relationships | enrollment_id, learner_id, course_id, enrolled_at |
| ContentItem | Course content hierarchy | content_id, course_id, content_type, sequence_no |
| ActivityEvent | Learner activity and event timestamps | event_id, enrollment_id, event_type, event_time_utc, received_at_utc, idempotency_key, issue_type |
| Assessment | Course assessments | assessment_id, course_id, passing_score, max_score |
| Attempt | Assessment submissions and scores | attempt_id, enrollment_id, assessment_id, attempt_number, submitted_at, score |
| CompletionRule | Course completion criteria | rule_id, course_id, min_content_completion_pct, require_assessment_pass |
| Cohort | Enrollment-month grouping | cohort_id, cohort_name, cohort_type, start_date, end_date |
| EnrollmentCohort | Enrollment-to-cohort mapping | enrollment_id, cohort_id, assigned_at |
| CourseOutcome | Calculated progress and completion status | outcome_id, enrollment_id, rule_id, content_completion_pct, assessment_passed, outcome_status, decision_reason |

## Key definitions

- **event_time_utc:** Time the activity occurred, stored in UTC.
- **received_at_utc:** Time the platform received the event, stored in UTC.
- **idempotency_key:** Identifier used to detect repeated logical events.
- **issue_type:** Optional label identifying an injected data-quality issue.
- **content_completion_pct:** Percentage of eligible course content completed.
- **assessment_passed:** Whether the required assessment pass condition is satisfied.
- **outcome_status:** Calculated course status: completed, in_progress, or not_completed.
- **cohort_type:** Type of cohort grouping, such as enrollment month, course, or program.

## Anomaly ground truth

`data/ground_truth.csv` is maintained separately from the exported feature tables. It identifies four deliberately injected anomaly types: duplicate events, activity without a valid enrollment, premature completion, and timezone shifts.

## Timestamp and reporting conventions

Store event timestamps in UTC. Convert to `Asia/Kolkata` when calculating reporting-day metrics for India. Preserve the original timestamps for auditing.

## Dataset scope

The current test dataset targets 100 learners, 10 courses, 300 enrollments, and 2,000 baseline activity events. Injected anomalies are additional labelled records.
