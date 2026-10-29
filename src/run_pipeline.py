
import subprocess
import sys


PIPELINE_STEPS = [
    ("Preflight safety check", "src.preflight_check"),
    ("Validate staging data", "src.validate_data"),
    ("Run data quality impact audit", "src.data_quality_audit"),
    ("Export staging data to CSV and JSON", "src.export_data"),
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
    print("\nLEARNGUARD ANALYTICS — SAFE TEST PIPELINE", flush=True)
    print("Database operations must target learnguard_staging.", flush=True)
    print("No automatic data generation, injection, or rebuilding.", flush=True)

    try:
        for description, module_name in PIPELINE_STEPS:
            run_step(description, module_name)

        print("\n" + "=" * 70, flush=True)
        print("PIPELINE FINISHED SUCCESSFULLY", flush=True)
        print("Validation, audit, and exports completed.", flush=True)
        print("=" * 70, flush=True)

    except RuntimeError as error:
        print(f"\nPIPELINE FAILED: {error}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
