
import subprocess
import sys


PIPELINE_STEPS = [
    ("Generate learners, courses, and enrollments", "src.generate_data"),
    ("Generate content and activity events", "src.generate_activities"),
    ("Generate assessments, attempts, and outcomes", "src.generate_assessments"),
    ("Validate generated data", "src.validate_data"),
    ("Create data quality impact report", "src.data_quality_audit"),
]


def run_step(description, module_name):
    print("\n" + "=" * 70, flush=True)
    print(f"STEP: {description}", flush=True)
    print("=" * 70, flush=True)

    result = subprocess.run(
        [sys.executable, "-m", module_name],
        check=False,
    )

    if result.returncode != 0:
        raise RuntimeError(
            f"Pipeline stopped: '{description}' failed "
            f"with exit code {result.returncode}."
        )


def main():
    print("LEARNGUARD ANALYTICS PIPELINE", flush=True)
    print("Configured mode and dataset size will be shown by src.config.", flush=True)

    try:
        for description, module_name in PIPELINE_STEPS:
            run_step(description, module_name)

        print("\n" + "=" * 70, flush=True)
        print("PIPELINE FINISHED", flush=True)
        print("All configured steps completed without a process error.")
        print("=" * 70, flush=True)

    except RuntimeError as error:
        print(f"\nPIPELINE FAILED: {error}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
