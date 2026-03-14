import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent  # src/


def run_phase(script: str, name: str):
    print(f"\n=== Running {name} ===")
    result = subprocess.run(
        [sys.executable, str(ROOT / script)],
    )
    if result.returncode != 0:
        print(f"{name} failed with exit code {result.returncode}. Stopping pipeline.")
        sys.exit(result.returncode)
    print(f"{name} completed.")


def main():
    run_phase("main.py", "Phase 1 (build structured CSVs)")
    run_phase("phase2_filter_with_llm.py", "Phase 2 (classify jobs)")
    run_phase("phase3_add_jd.py", "Phase 3 (add JD for apply-now jobs)")


if __name__ == "__main__":
    main()
