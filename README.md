# LearnGuard Analytics

## 1. Overview

LearnGuard Analytics is a learning analytics and data quality project designed to analyze learner participation, course activity, assessment progress, and course completion.

The project uses MySQL, Python, synthetic learning activity data, data validation, and a Data Quality Impact Audit to identify issues that can distort learning analytics.

It demonstrates relational data modeling, synthetic data generation, anomaly detection, data validation, reproducible exports, and REST API development.

## 2. Key Features

- Relational MySQL database with primary and foreign key constraints.
- Synthetic learner, course, enrollment, assessment, and activity data.
- Large-scale activity CSV generation using a fixed random seed.
- CSV and JSON exports for downstream analysis.
- Referential integrity and date consistency validation.
- Four labeled data quality anomalies.
- Ground-truth labels for evaluating anomaly detection.
- Data Quality Impact Audit with recommended corrective actions.
- Source manifest containing export counts and checksums.
- FastAPI endpoints for learner mastery, recommendations, learning paths, and learning content.

## 3. Technology Stack

- **Language:** Python
- **Database:** MySQL 8.0
- **API:** FastAPI
- **Data processing:** pandas
- **Database connectivity:** mysql-connector-python
- **Configuration:** python-dotenv
- **Data formats:** CSV and JSON
- **API documentation:** OpenAPI / Swagger UI
- **Version control:** Git and GitHub

## 4. Dataset Status

### 4.1 Current MySQL staging dataset

The current MySQL staging database, `learnguard_staging`, contains the following records.

| Entity | Records |
|---|---:|
| Learners | 100 |
| Courses | 10 |
| Enrollments | 300 |
| Content items | 40 |
| Activity events | 2,003 |
| Assessments | 10 |
| Assessment attempts | 300 |
| Completion rules | 10 |
| Cohorts | 9 |
| Enrollment-cohort assignments | 300 |
| Course outcomes | 301 |

The activity table contains 2,000 baseline events and three additional flagged anomaly events. A separate anomalous course outcome is also present.

### 4.2 Generated full-scale activity CSV

A separate synthetic activity dataset was generated at:

`data/generated_activity_preview.csv`

| Property | Value |
|---|---|
| Baseline activity rows | 2,000,000 |
| Columns | 11 |
| File size | 388,389,218 bytes |
| Random seed | 20261022 |
| SHA-256 | `3328b71e92ea87ed0cd0c7b68f1c69c6da0e06880ef6a060027987581534961a` |
| Database written by generator | No |

The CSV passed the row-count and column-count checks. Event IDs and idempotency keys were generated deterministically using the configured seed.

**Important scope distinction:** The two-million-event CSV was generated separately from MySQL. The complete relational dataset has not yet reached the full-scale target of 20,000 learners, 500 courses, and 100,000 enrollments. The CSV should not be interpreted as proof that those relational tables have been populated at full scale.

## 5. Data Quality Anomalies

The project includes four labeled anomaly types.

### 5.1 Duplicate activity events

Repeated idempotency keys can cause the same logical activity to be counted more than once, inflating engagement metrics.

**Recommended action:** Identify repeated keys and deduplicate logical activity for analytical calculations while preserving original source records.

### 5.2 Activity from an unenrolled learner

An activity event may refer to a learner who does not have a valid enrollment for the associated course.

**Recommended action:** Validate learner-enrollment relationships and exclude or quarantine confirmed invalid events from enrollment-based metrics.

### 5.3 Premature completion

A course outcome may be marked completed before the required assessment has been passed.

**Recommended action:** Recalculate completion using assessment timestamps and the applicable completion rules.

### 5.4 Timezone-related reporting-day shift

An event timestamp in UTC may fall on a different calendar date when converted to the reporting timezone, Asia/Kolkata.

**Recommended action:** Preserve timestamps in UTC and convert them to the reporting timezone when calculating daily metrics.

### Ground-truth labels

The anomaly labels are maintained separately in:

`data/ground_truth.csv`

This file contains the anomaly ID, anomaly type, affected entity, expected issue, and severity. Ground-truth labels should not be used as ordinary predictive input features.

## 6. Data Quality Impact Audit

The Data Quality Impact Audit identifies the four anomaly types and explains their potential impact on analytics.

The current audit reported:

| Anomaly | Detected | Metric impact |
|---|---:|---|
| Duplicate event | 1 | One excess activity row |
| Unenrolled activity | 1 | One event fails the enrollment relationship check |
| Premature completion | 1 | One completion record is ineligible |
| Timezone shift | 1 | One reporting-day mismatch |

The report includes before-and-after metric values and recommended corrective actions.

Output file:

`reports/data_quality_impact_audit.csv`

The audit preserves source records and documents analytical corrections rather than silently deleting data.

## 7. Project Structure

```text
LearnGuard-Analytics/
├── data/
│   ├── exports/
│   ├── generated_activity_preview.csv
│   ├── ground_truth.csv
│   └── source_manifest.json
├── docs/
│   ├── data_dictionary.md
│   └── validation_summary.md
├── reports/
│   └── data_quality_impact_audit.csv
├── src/
│   ├── api.py
│   ├── config.py
│   ├── controlled_rebuild.py
│   ├── data_quality_audit.py
│   ├── db_connection.py
│   ├── export_data.py
│   ├── generate_activities.py
│   ├── generate_assessments.py
│   ├── generate_data.py
│   ├── preflight_check.py
│   ├── run_pipeline.py
│   └── validate_data.py
├── .gitignore
├── PROJECT_PLAN.md
├── README.md
└── requirements.txt
```

## 8. Installation and Setup

### Prerequisites

- Python 3.10 or later
- MySQL 8.0
- Git

### Step 1: Clone the repository

```powershell
git clone https://github.com/kaladhar06/LearnGuard-Analytics.git
cd LearnGuard-Analytics
```

### Step 2: Create a virtual environment

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

### Step 3: Install dependencies

```powershell
pip install -r requirements.txt
```

### Step 4: Configure the environment

Create a local `.env` file in the project root.

```text
DB_HOST=127.0.0.1
DB_PORT=3306
DB_USER=root
DB_PASSWORD=your_local_password
DB_NAME=learnguard_staging
LEARNGUARD_DATASET_MODE=full
LEARNGUARD_SEED=20261022
```

Replace the example password with your local MySQL password.

**Security:** Never commit `.env`, passwords, or database backups to GitHub.

### Step 5: Prepare the database

Ensure the required schema and test data exist in `learnguard_staging` before running the database validation, audit, or export scripts.

The original `learnguard_analytics` database must not be used as a target for test or generation writes.

## 9. Generating Activity Data

The activity generator can create a synthetic CSV using the configured event count.

Run:

```powershell
python -m src.generate_activities
```

The generated file is:

`data/generated_activity_preview.csv`

The generator reads enrollment and content information from `learnguard_staging` and writes generated activity events to CSV. It does not insert the generated events into MySQL.

The configured full mode specifies two million baseline events. The current CSV has been verified to contain exactly 2,000,000 data rows and 11 columns.

The generator depends on the enrollments and course content already present in the staging database. It does not create the full set of learners, courses, or enrollments.

## 10. Data Validation and Export

### Run the complete safe pipeline

```powershell
python -m src.run_pipeline
```

The pipeline performs:

1. Database preflight checks.
2. Staging data validation.
3. Data Quality Impact Audit.
4. CSV and JSON exports.
5. Source manifest generation.

### Run validation separately

```powershell
python -m src.validate_data
```

### Run the audit separately

```powershell
python -m src.data_quality_audit
```

### Export database tables

```powershell
python -m src.export_data
```

The exports are written to `data/exports/`, the manifest to `data/source_manifest.json`, and the audit report to `reports/data_quality_impact_audit.csv`.

Run database-modifying scripts only after reviewing their database target and safety checks. Do not run untested rebuild scripts against a database containing data you need to preserve.

## 11. REST API

The project provides a FastAPI backend for learner progress, recommendations, learning paths, and learning-content access.

### Start the API

```powershell
python -m uvicorn src.api:app --reload
```

Open the interactive API documentation:

http://127.0.0.1:8000/docs

### Available endpoints

| Method | Endpoint | Description |
|---|---|---|
| GET | `/` | API information |
| GET | `/health` | API and database health check |
| GET | `/learners/{learner_id}/mastery` | Retrieve learner course progress |
| GET | `/learners/{learner_id}/recommendations` | Retrieve learning recommendations |
| POST | `/learners/{learner_id}/learning-paths` | Generate a learning path response |
| GET | `/learners/{learner_id}/courses/{course_id}/learning-content` | Retrieve enrolled course content |

### API limitations

- The API has been tested against the current staging dataset.
- The learning-path endpoint returns a response but does not persist a learning-path record.
- API results depend on the data available in the staging database.

## 12. Validation Results

The current staging dataset passed nine structural validation checks.

Two review flags remain intentionally present:

1. A repeated event idempotency key.
2. Activity from an unenrolled learner.

The Data Quality Impact Audit detects all four labeled anomaly types, including the premature completion and timezone-related reporting-day shift.

The two-million-event CSV has passed row-count and column-count checks. Full-scale population and validation of all relational tables remain outstanding.

## 13. Reproducibility and Data Quality Principles

- Use a fixed random seed for reproducible synthetic generation.
- Record dataset sizes and checksums in the source manifest.
- Validate primary-key and foreign-key relationships.
- Check date ordering and lifecycle consistency.
- Preserve original source records when identifying anomalies.
- Keep ground-truth labels separate from analytical input features.
- Store event timestamps in UTC and convert them for local reporting.
- Distinguish expected test anomalies from unexpected validation failures.
- Verify exported row counts and file checksums.

## 14. Known Limitations

- The MySQL database currently contains the test-scale relational dataset.
- The two-million-event CSV is separate from the MySQL activity table.
- The full-scale targets for learners, courses, and enrollments have not yet been populated and validated.
- Two anomaly-related validation checks require review because of intentionally introduced test anomalies.
- The learning-path API endpoint does not persist generated paths.
- The generated activity CSV is a large local artifact and should not be committed to GitHub unless the submission instructions and repository storage approach explicitly support it.

## 15. Security

- Keep credentials in a local `.env` file.
- Never publish passwords or sensitive connection settings.
- Do not commit database backups or virtual-environment files.
- Use `learnguard_staging` for test and validation operations.
- Preserve the original `learnguard_analytics` database.
- Review database-modifying scripts before execution.

## 16. Repository

GitHub: https://github.com/kaladhar06/LearnGuard-Analytics

---

**Project summary:** LearnGuard Analytics demonstrates synthetic learning activity generation, relational data validation, anomaly detection, a Data Quality Impact Audit, reproducible CSV/JSON exports, and a FastAPI backend. The two-million-event CSV is generated and verified; full-scale population of the complete relational dataset remains future work.