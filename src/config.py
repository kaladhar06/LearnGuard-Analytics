
import os

# Reproducible seed for synthetic data generation
SEED = int(os.getenv("LEARNGUARD_SEED", "20261022"))

# Dataset size: "test" for development, "full" for challenge output
DATASET_MODE = os.getenv("LEARNGUARD_DATASET_MODE", "test").lower()

DATASET_SIZES = {
    "test": {
        "NUM_LEARNERS": 100,
        "NUM_COURSES": 10,
        "NUM_ENROLLMENTS": 300,
        "NUM_EVENTS": 2000,
    },
    "full": {
        "NUM_LEARNERS": 20000,
        "NUM_COURSES": 500,
        "NUM_ENROLLMENTS": 100000,
        "NUM_EVENTS": 2000000,
    },
}

if DATASET_MODE not in DATASET_SIZES:
    raise ValueError(
        "Invalid LEARNGUARD_DATASET_MODE. Use 'test' or 'full'."
    )

NUM_LEARNERS = DATASET_SIZES[DATASET_MODE]["NUM_LEARNERS"]
NUM_COURSES = DATASET_SIZES[DATASET_MODE]["NUM_COURSES"]
NUM_ENROLLMENTS = DATASET_SIZES[DATASET_MODE]["NUM_ENROLLMENTS"]
NUM_EVENTS = DATASET_SIZES[DATASET_MODE]["NUM_EVENTS"]

print(f"LearnGuard dataset mode: {DATASET_MODE}")
print(f"Learners: {NUM_LEARNERS:,}")
print(f"Courses: {NUM_COURSES:,}")
print(f"Enrollments: {NUM_ENROLLMENTS:,}")
print(f"Activity events: {NUM_EVENTS:,}")
