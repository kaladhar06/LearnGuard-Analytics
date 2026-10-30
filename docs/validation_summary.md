
# LearnGuard Analytics — Final Validation Summary

## 1. Validation Overview

Final validation was executed against the `learnguard_staging` database.

Command:

```bash
python -m src.validate_data
```

Result:
- 9 structural validation checks passed.
- 2 review conditions were identified.
- Both review conditions correspond to intentionally retained anomaly records.

## 2. Full-Scale Dataset Summary

| Dataset component | Verified records |
|---|---:|
| Learners | 20,000 |
| Courses | 500 |
| Enrollments | 100,000 |
| Content items | 2,000 |
| Activity events in separate CSV | 2,000,000 |
| ActivityEvent database records | 2,003 |
| Assessments | 500 |
| Attempts | 300 |
| Completion rules | 500 |
| Course outcomes | 301 |
| Cohorts | 19 |
| Enrollment-cohort assignments | 100,000 |

**Important:** The two-million-event baseline dataset is delivered as a separate CSV file. The MySQL `ActivityEvent` table contains 2,003 records, consisting of 2,000 baseline records and 3 additional flagged records.

## 3. Structural Validation Results

| Validation check | Result |
|---|---|
| Enrollments with missing learners | PASS — 0 |
| Enrollments with missing courses | PASS — 0 |
| Events with missing enrollment references | PASS — 0 |
| Events with mismatched learner and enrollment | PASS — 0 |
| Events referencing content from another course | PASS — 0 |
| Attempts referencing assessments from another course | PASS — 0 |
| Outcomes referencing rules from another course | PASS — 0 |
| Invalid assessment date ranges | PASS — 0 |
| Invalid enrollment date ordering | PASS — 0 |
| Repeated event idempotency keys | REVIEW — 1 |
| Activity from unenrolled learners | REVIEW — 1 |

The two review conditions are intentional and are retained for anomaly detection and audit purposes.

## 4. Anomaly Detection Results

Four anomaly scenarios were detected by the Data Quality Impact Audit.

| Anomaly | Detected | Before correction | After correction |
|---|---:|---:|---:|
| Duplicate event | 1 | 2,003 logical activity rows | 2,002 |
| Unenrolled activity | 1 | 2,003 eligible activity rows | 2,002 |
| Premature completion | 1 | 1 eligible completion record | 0 |
| Timezone shift | 1 | 1 reporting-day mismatch | 0 |

### Anomaly handling decisions

1. Duplicate events: use idempotency keys to prevent duplicate logical activity from inflating engagement metrics.
2. Unenrolled activity: exclude or quarantine confirmed invalid events from enrollment-based metrics.
3. Premature completion: recalculate completion using assessment timestamps and applicable completion rules.
4. Timezone shift: retain UTC timestamps and convert them to Asia/Kolkata for reporting dates.

Original records are preserved. Corrections are applied to analytical calculations rather than silently deleting source records.

## 5. Data Quality Impact Audit

Command:

```bash
python -m src.data_quality_audit
```

Report location:

`reports/data_quality_impact_audit.csv`

The audit compares metric values before and after approved data-quality handling decisions and records the impact of each detected anomaly.

Verified results:
- Duplicate event detected: 1
- Unenrolled activity detected: 1
- Premature completion detected: 1
- Timezone shift detected: 1

## 6. Ground Truth

The separate `data/ground_truth.csv` file contains four labelled anomaly records:

- ANOM-001: duplicate event
- ANOM-002: unenrolled activity
- ANOM-003: premature completion
- ANOM-004: timezone shift

Ground-truth labels are maintained separately from analytical input features.

## 7. Dataset Export and Integrity

The project exports database tables in CSV and JSON formats.

The source manifest is maintained at:

`data/source_manifest.json`

It records:
- Database and dataset configuration.
- Table row counts.
- CSV and JSON file locations.
- Export checksums.
- Two-million-event CSV metadata.
- SHA256 checksum of the generated activity dataset.

The generated activity CSV contains 2,000,000 rows and 11 columns.

## 8. API Verification

The following API endpoints were successfully tested:

| Endpoint | Result |
|---|---|
| GET /health | PASS |
| GET /learners/{learner_id}/mastery | PASS |
| GET /learners/{learner_id}/recommendations | PASS |
| GET /learners/{learner_id}/courses/{course_id}/learning-content | PASS |

The API health endpoint confirmed connection to `learnguard_staging`.

## 9. Limitations and Remaining Work

- The full two-million-event baseline is delivered as a separate CSV, not imported into the MySQL ActivityEvent table.
- The Attempt table currently contains 300 records.
- The CourseOutcome table currently contains 301 records.
- Automated test coverage and broader reproducibility testing remain to be completed.

## 10. Final Validation Statement

The staging database passed all nine structural validation checks. Two expected review conditions were retained for intentional anomaly scenarios.

The Data Quality Impact Audit successfully detected all four required anomaly types.

The full-scale master data, separate two-million-event CSV, exports, manifest, and tested API endpoints were verified.

This report reflects the observed validation results and the remaining limitations at the time of final testing.
