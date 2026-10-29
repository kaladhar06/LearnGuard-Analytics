
# LearnGuard Analytics

## 1. Problem Statement
Online learning platforms need reliable insights into learner engagement,
assessment progress, and course completion. Duplicate or invalid activity
records can produce misleading reports.

## 2. Project Objective
Build a reproducible learning analytics system that generates synthetic
learning data, calculates performance metrics, detects anomalies, and
explains the decisions made from the data.

## 3. Unique Feature
Implement an Explainable Data Quality Impact Audit that:
- Detects duplicate activity events.
- Identifies activity from unenrolled learners.
- Flags completions that violate assessment requirements.
- Detects timezone-related reporting errors.
- Compares metrics before and after approved corrections.
- Preserves original records and records every correction decision.

## 4. Main Users
- Learners
- Instructors
- Academic administrators
- Support staff
- Platform administrators

## 5. Key Metrics
- Weekly active learner rate
- Content engagement rate
- Assessment pass rate
- Course completion rate
- At-risk learner count
- Data anomaly rate
- Metric change after data-quality corrections

## 6. Technology
- Python
- SQL
- Power BI
- CSV and JSON
- Git and GitHub

## 7. Data Policy
Use synthetic learner data. Keep anomaly ground-truth labels
separate from analytical input data.

## 8. Quality Goals
- Reproducible data generation using a fixed seed.
- Valid primary and foreign keys.
- Documented business rules.
- Automated validation and tests.
- Traceable anomaly decisions.
