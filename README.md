# LearnGuard Analytics

## Overview

LearnGuard Analytics is a data quality and learning analytics project designed to analyze learner participation, course activity, assessment progress, and course completion.

The project uses a relational MySQL database, Python-based data validation, synthetic learning activity data, and a data quality impact audit to identify issues that can distort learning analytics.

## Key Features

- Synthetic learner, course, enrollment, assessment, and activity data.
- MySQL relational schema with primary and foreign key relationships.
- CSV and JSON exports for downstream analysis.
- Data validation for referential integrity, course consistency, and date ordering.
- Four labeled test anomalies:
  - Duplicate activity events
  - Activity from an unenrolled learner
  - Completion recorded before a required assessment pass
  - Timezone-related reporting-day shift
- Data Quality Impact Audit with recommended corrective actions.
- Ground-truth labels for evaluating anomaly detection.
- Source manifest containing export counts and checksums.

## Technology Stack

- Python
- MySQL 8.0
- pandas
- mysql-connector-python
- python-dotenv
- CSV and JSON

## Current Test Dataset

The current test dataset contains:

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

The activity dataset includes 2,000 baseline events and three additional flagged activity records. A separate completion anomaly is also included.

**Scope note:** These are test-dataset results. The full-scale target of 20,000 learners, 500 courses, 100,000 enrollments, and 2 million activity events has not yet been generated and validated.

## Project Structure

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
└── requirements.txt
```

## Setup

1. Install Python and MySQL 8.0.
2. Create and activate a virtual environment:

   ```powershell
   python -m venv .venv
   .venv\Scripts\Activate.ps1
   ```

3. Install dependencies:

   ```powershell
   pip install -r requirements.txt
   ```

4. Create a local `.env` file with your MySQL connection settings:

   ```text
   DB_HOST=127.0.0.1
   DB_PORT=3306
   DB_USER=root
   DB_PASSWORD=your_local_password
   DB_NAME=learnguard_staging
   ```

   Replace the example password with your own local configuration. Never commit `.env` to Git.

5. Ensure the required schema and test data exist in `learnguard_staging` before running the audit or export scripts.

## Validation and Export

Run the validation checks:

```powershell
python -m src.validate_data
```

Generate the data quality impact audit:

```powershell
python -m src.data_quality_audit
```

Export the staging database tables:

```powershell
python -m src.export_data
```

The exports are written to `data/exports/`, the source manifest to `data/source_manifest.json`, and the audit report to `reports/data_quality_impact_audit.csv`.

Run database-modifying scripts only after reviewing their target database and safety checks.

## Data Quality Principles

- Preserve original source records.
- Detect and document anomalies instead of silently deleting them.
- Keep timestamps in UTC and convert to the reporting timezone when needed.
- Distinguish expected test anomalies from unexpected validation failures.
- Use ground-truth labels separately from analytical input features.
- Record export counts and checksums to support reproducibility.

## Current Validation Status

The current test dataset passed nine structural validation checks. Two review flags remain intentionally present: one repeated event idempotency key and one unenrolled activity event.

The data quality audit detects all four labeled anomaly types. Full-scale generation and validation remain future work.

## Security

Local environment files, virtual environments, and database backups are excluded from version control. Do not publish credentials, production data, or database backup files.
