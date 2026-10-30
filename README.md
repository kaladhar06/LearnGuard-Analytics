# LearnGuard Analytics

### Learning Analytics, Synthetic Data Engineering & Data Quality Impact Auditing

LearnGuard Analytics is a learning analytics project designed to organize learner activity data, monitor learning progress, identify data-quality anomalies, and provide insights through a Python-based REST API.

The project combines synthetic educational data generation, MySQL database management, data validation, anomaly detection, CSV/JSON exports, and explainable data-quality impact auditing.

---

## 1. Project Overview

Online learning platforms generate large amounts of data through learner enrollments, course interactions, assessments, learning activities, and course completions.

However, inaccurate or inconsistent records can affect engagement metrics, learner progress calculations, and reporting.

LearnGuard Analytics addresses these challenges by:

- Creating a large synthetic educational dataset.
- Managing learner, course, enrollment, and activity information using MySQL.
- Identifying data-quality issues and intentionally introduced anomalies.
- Validating relationships and data consistency.
- Measuring the impact of anomalies on learning analytics.
- Providing learner mastery, recommendations, and learning-path information through REST API endpoints.
- Exporting structured datasets for further analysis.

## 2. Project Objectives

1. Build a synthetic learning analytics dataset.
2. Manage educational entities and relationships using MySQL.
3. Generate and maintain a 2-million-row learner activity CSV dataset.
4. Identify and analyze four different categories of data anomalies.
5. Validate primary relationships, foreign-key references, and data consistency.
6. Measure how data-quality issues affect analytical results.
7. Develop REST API endpoints using FastAPI.
8. Export database tables into CSV and JSON formats.
9. Document the dataset, validation results, and data-quality findings.

## 3. Technology Stack

| Category | Technologies |
|---|---|
| Programming Language | Python |
| Database | MySQL 8.0 |
| Backend Framework | FastAPI |
| API Server | Uvicorn |
| Data Processing | Pandas |
| Database Connectivity | mysql-connector-python |
| Environment Configuration | python-dotenv |
| API Documentation | Swagger UI / OpenAPI |
| Testing | Python unittest and unittest.mock |
| Data Formats | CSV, JSON, SQL |

## 4. Dataset Configuration

The project includes a synthetic educational dataset with the following target configuration:

| Dataset Component | Records |
|---|---:|
| Learners | 20,000 |
| Courses | 500 |
| Enrollments | 100,000 |
| Content Items | 2,000 |
| Baseline Activity Events | 2,000,000 |

Additional database entities include assessments, attempts, completion rules, course outcomes, cohorts, and enrollment-cohort relationships.

### Actual database records

The final staging database validation confirmed the following:

| Database Table | Actual Records |
|---|---:|
| Learner | 20,000 |
| Course | 500 |
| Enrollment | 100,000 |
| ContentItem | 2,000 |
| ActivityEvent | 2,003 |
| Assessment | 500 |
| Attempt | 300 |
| CompletionRule | 500 |
| CourseOutcome | 301 |
| Cohort | 19 |
| EnrollmentCohort | 100,000 |

**Important dataset distinction:**

The 2-million-event baseline dataset is maintained as a separate CSV file:

`data/generated_activity_preview.csv`

The MySQL `ActivityEvent` table contains 2,003 records. The two datasets are separate and should not be confused.

## 5. Synthetic Activity Dataset

The large-scale activity dataset contains 2,000,000 data rows and 11 columns.

It represents learner interactions with an online learning platform.

The synthetic activity scenarios include:

- Inactive learners.
- Mobile and offline activity synchronization.
- Late-arriving events.
- Repeated attempts.
- Learner activity records used for engagement analysis.

The generated CSV file is maintained separately from the MySQL activity table.

### Dataset integrity

The final audit verified:

- The CSV file exists.
- It contains exactly 2,000,000 data rows.
- It contains the expected 11 columns.
- The desktop backup matches the main CSV file.
- The SHA-256 checksum matches the recorded dataset checksum.

**SHA-256:**

`2e12a0c6b183dd23e0e38da4abe42a7c424aa8e262ff63586230a23b45faddcc`

The dataset configuration uses seed `20261022`.

## 6. Data Quality Anomalies

Four categories of anomalies were intentionally introduced and analyzed.

### 1. Duplicate Events

Repeated activity events can inflate engagement measurements.

**Impact:** The number of logical activity events can be overstated.

### 2. Activity from Unenrolled Learners

Activity records may exist for learners who are not enrolled in the corresponding course.

**Impact:** Such records can incorrectly contribute to eligible course activity metrics.

### 3. Premature Completion

A course completion may be recorded before the required assessment has been completed.

**Impact:** Completion metrics can incorrectly represent learner progress.

### 4. Timezone Shifts

Timezone conversion issues can assign activity events to incorrect reporting days.

**Impact:** Daily activity and engagement reports can become inaccurate.

## 7. Data Quality Impact Audit

One of the main features of LearnGuard Analytics is its explainable Data Quality Impact Audit.

It evaluates how identified anomalies affect analytical measurements before and after approved corrections or exclusions.

The audit records the anomaly category, affected records, and the corresponding metric impact.

### Audit results

| Anomaly | Before | After |
|---|---:|---:|
| Duplicate events | 2,003 logical activity rows | 2,002 |
| Unenrolled activity | 2,003 eligible activity rows | 2,002 |
| Premature completion | 1 eligible completion record | 0 |
| Timezone shift | 1 reporting-day mismatch | 0 |

The audit report is generated at:

`reports/data_quality_impact_audit.csv`

The report contains four anomaly records.

The objective is not just to detect data-quality issues, but also to explain how they can affect learning analytics and reporting.

## 8. Data Validation

The project includes automated structural and relationship validation.

The latest validation confirmed nine structural checks passed.

### Validation checks

1. Missing learner enrollment references.
2. Missing course enrollment references.
3. Activity events with missing enrollment references.
4. Learner and enrollment mismatches.
5. Activity events referencing content from another course.
6. Assessment attempts referencing assessments from another course.
7. Course outcomes referencing rules from another course.
8. Invalid assessment date ranges.
9. Invalid enrollment date ordering.

### Expected anomaly reviews

Two checks are marked REVIEW because of intentionally introduced anomalies:

- Repeated event idempotency keys.
- Activity from unenrolled learners.

These are expected findings, not unexpected structural validation failures.

## 9. Database Exports

The project exports its database tables into CSV and JSON formats.

The exported tables include:

- Learner
- Course
- Enrollment
- ContentItem
- ActivityEvent
- Assessment
- Attempt
- CompletionRule
- CourseOutcome
- Cohort
- EnrollmentCohort

The CSV exports were checked against the actual staging database row counts.

The project also maintains:

- `data/ground_truth.csv` — contains the four anomaly labels.
- `data/source_manifest.json` — contains dataset configuration and source metadata.
- `reports/data_quality_impact_audit.csv` — contains the data-quality impact findings.

The ground-truth labels are maintained separately from the activity input data.

## 10. REST API Development

LearnGuard Analytics includes a REST API developed using FastAPI.

The API provides learner-level analytics and learning information.

### Available endpoints

| Method | Endpoint | Description |
|---|---|---|
| GET | `/` | Project information and API status |
| GET | `/health` | API and database health check |
| GET | `/learners/{learner_id}/mastery` | Retrieves learner course mastery |
| GET | `/learners/{learner_id}/recommendations` | Retrieves learning recommendations |
| POST | `/learners/{learner_id}/learning-paths` | Generates a learning path |
| GET | `/learners/{learner_id}/courses/{course_id}/learning-content` | Retrieves course learning content |

### API documentation

FastAPI automatically provides interactive Swagger documentation.

Once the API server is running, access:

`http://127.0.0.1:8000/docs`

### API verification

The following were manually verified:

- Root endpoint.
- Health endpoint.
- Learner mastery.
- Learner recommendations.
- Learning content retrieval.
- Learning-path generation.

The API health endpoint confirmed the `learnguard_staging` database.

## 11. Automated API Testing

The project includes automated API tests using Python's built-in `unittest` framework and mocking.

Test file:

`tests/test_api.py`

### Test coverage

| Test Case | Result |
|---|---|
| Root endpoint | PASS |
| Health endpoint | PASS |
| Learner mastery | PASS |
| Learning content | PASS |
| Learning-path generation | PASS |
| Missing learner returns 404 | PASS |
| Recommendations | PASS |

**Final test result: 7/7 tests passed.**

### Run automated tests

```bash
python -m unittest discover -s tests -v
```

The API tests mock database-fetch operations and do not require database writes.

## 12. Project Structure

```text
LearnGuard-Analytics/
│
├── data/
│   ├── generated_activity_preview.csv
│   ├── ground_truth.csv
│   └── source_manifest.json
│
├── docs/
│   ├── data_dictionary.md
│   └── validation_summary.md
│
├── exports/
│   ├── CSV exports
│   └── JSON exports
│
├── reports/
│   └── data_quality_impact_audit.csv
│
├── src/
│   ├── api.py
│   ├── validate_data.py
│   ├── data_quality_audit.py
│   ├── run_pipeline.py
│   └── other project modules
│
├── tests/
│   └── test_api.py
│
├── PROJECT_PLAN.md
├── README.md
├── requirements.txt
└── final_submission_check.py
```

*The structure above highlights the main project components; additional source files and local inspection files may also exist.*

## 13. Installation and Setup

### Prerequisites

- Python 3.x
- MySQL 8.0
- Visual Studio Code
- Git

### Step 1: Clone the repository

```bash
git clone https://github.com/kaladhar06/LearnGuard-Analytics.git
```

```bash
cd LearnGuard-Analytics
```

### Step 2: Create a virtual environment

```bash
python -m venv .venv
```

Activate it on Windows PowerShell:

```powershell
.venv\Scripts\Activate.ps1
```

### Step 3: Install dependencies

```bash
pip install -r requirements.txt
```

### Step 4: Configure database connection

Create or configure the `.env` file with the appropriate MySQL connection settings.

Use the staging database for project validation and testing.

Verify the configured database before running any database-writing scripts.

### Step 5: Run the API

```bash
uvicorn src.api:app --reload
```

Open:

- API: `http://127.0.0.1:8000/`
- Health: `http://127.0.0.1:8000/health`
- Swagger: `http://127.0.0.1:8000/docs`

## 14. Running Validation and Audit

Run structural data validation:

```bash
python -m src.validate_data
```

Run the data-quality impact audit:

```bash
python -m src.data_quality_audit
```

Run the complete project pipeline:

```bash
python -m src.run_pipeline
```

The pipeline uses the configured project database. Verify that it is configured for `learnguard_staging` before executing it.

### Final read-only submission audit

```bash
python final_submission_check.py
```

This checks:

- Staging database record counts.
- Two-million-row activity CSV.
- CSV checksum.
- Desktop backup integrity.
- Database table exports.
- Ground-truth anomaly labels.
- Data-quality impact audit.
- Source manifest validity.

The final submission audit is read-only and does not insert, update, or delete database records.

## 15. Project Limitations and Notes

The following limitations are documented transparently:

1. The MySQL `ActivityEvent` table contains 2,003 rows, while the separate baseline activity CSV contains 2,000,000 rows.
2. The `Attempt` table contains 300 records.
3. The `CourseOutcome` table contains 301 records.
4. Two structural validation checks are marked REVIEW because they correspond to intentionally introduced anomalies.
5. Full-scale automated database integration testing and end-to-end reproducibility have not been established by the final submission checks.

The dataset and its backup should be preserved. Do not overwrite the original generated activity CSV during final submission preparation.

## 16. Final Verification Summary

The final submission audit confirmed:

- 11 database table counts matched expected values.
- The 2-million-row activity CSV was verified.
- The CSV contained 11 expected columns.
- The desktop backup matched the main dataset.
- All 11 CSV table exports matched expected row counts.
- Four ground-truth anomaly labels were present.
- Four data-quality impact audit records were present.
- The source manifest was valid JSON.
- All seven automated API tests passed.
- The API root, health, and Swagger documentation endpoints worked successfully.

The project was maintained and tested using the `learnguard_staging` database.

---

## 17. Conclusion

LearnGuard Analytics demonstrates how synthetic educational data can be structured, validated, analyzed, and exposed through a Python-based REST API.

The project combines database management, large-scale activity data handling, data-quality validation, anomaly detection, explainable impact auditing, and API development.

It provides a foundation for understanding how data-quality issues influence learning analytics and how reliable data validation can improve the accuracy of learner progress and engagement reporting.

**Project:** LearnGuard Analytics  
**Repository:** https://github.com/kaladhar06/LearnGuard-Analytics  
**Primary Technologies:** Python, MySQL, FastAPI, Pandas, CSV, JSON