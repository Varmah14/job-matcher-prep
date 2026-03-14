import csv
import json
import os
from pathlib import Path
from typing import Dict, Any, List
from html.parser import HTMLParser


# Folders
PHASE1_INPUT_FOLDER_NAME = "input_files"  # original JSON files
PHASE2_FOLDER_NAME = "output_phase2_classified"  # phase 2 outputs
PHASE3_OUTPUT_NAME = "output_phase3_apply_now_with_jd.csv"

# Phase 2 column names
PHASE2_JOB_ID_COL = "id"  # same as in Phase 1 CSVs
PHASE2_CLASS_COL = "classification"
APPLY_NOW_VALUE = "apply now"  # exact label from Phase 2

# Original JSON structure
JSON_RESULTS_KEY = "results"
JSON_ID_FIELD = "id"
JSON_JOB_INFO_KEY = "job_information"
JSON_V5_KEY = "v5_processed_job_data"

# Fields inside those structures
JSON_JD_FIELD = "description"  # under job_information
JSON_TITLE_FIELD = "title"  # under job_information
JSON_COMPANY_FIELD = "company_name"  # under v5_processed_job_data
JSON_APPLY_URL_FIELD = "apply_url"  # top-level on job


class HTMLStripper(HTMLParser):
    def __init__(self):
        super().__init__()
        self.text_parts: List[str] = []

    def handle_data(self, data: str) -> None:
        self.text_parts.append(data)

    def get_text(self) -> str:
        return " ".join(part.strip() for part in self.text_parts if part.strip())


def strip_html(html_string: str) -> str:
    if not html_string:
        return ""
    stripper = HTMLStripper()
    stripper.feed(html_string)
    return stripper.get_text()


def build_jobs_index_from_input_files(input_folder: Path) -> Dict[str, Dict[str, Any]]:
    if not input_folder.exists():
        raise FileNotFoundError(f"Input folder not found: {input_folder}")

    json_files = sorted(f for f in os.listdir(input_folder) if f.endswith(".json"))
    if not json_files:
        print(f"No JSON files found in {input_folder}")
        return {}

    print(
        f"Phase 3: found {len(json_files)} JSON file(s) in {input_folder}: {json_files}"
    )

    jobs_by_id: Dict[str, Dict[str, Any]] = {}
    total_jobs = 0

    for filename in json_files:
        path = input_folder / filename
        try:
            if path.stat().st_size == 0:
                print(f"  ⧗ {filename} → Skipped (empty file)")
                continue
        except OSError as e:
            print(f"  ✗ {filename} → Error checking size: {e}")
            continue

        try:
            with path.open("r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            print(f"  ✗ {filename} → Error loading JSON: {e}")
            continue

        results = data.get(JSON_RESULTS_KEY, [])
        for job in results:
            job_id = job.get(JSON_ID_FIELD)
            if job_id is None:
                continue
            jobs_by_id[str(job_id)] = job
            total_jobs += 1

        print(f"  ✓ {filename} → {len(results)} jobs")

    print(
        f"\nPhase 3: indexed {len(jobs_by_id)} unique job ids (total jobs seen: {total_jobs})"
    )
    return jobs_by_id


def read_phase2_apply_now_rows(phase2_folder: Path) -> List[dict]:
    if not phase2_folder.exists():
        raise FileNotFoundError(f"Phase 2 folder not found: {phase2_folder}")

    csv_files = sorted(f for f in os.listdir(phase2_folder) if f.endswith(".csv"))
    if not csv_files:
        print(f"No Phase 2 CSV files found in {phase2_folder}")
        return []

    apply_rows: List[dict] = []
    print(f"Phase 3: scanning {len(csv_files)} Phase 2 CSV file(s): {csv_files}")

    for filename in csv_files:
        path = phase2_folder / filename
        with path.open("r", encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                label = (row.get(PHASE2_CLASS_COL) or "").strip().lower()
                if label == APPLY_NOW_VALUE:
                    apply_rows.append(row)

    print(f"Phase 3: found {len(apply_rows)} 'apply now' rows across all Phase 2 CSVs.")
    return apply_rows


def main():
    project_root = Path(__file__).resolve().parent.parent
    input_folder = project_root / PHASE1_INPUT_FOLDER_NAME
    phase2_folder = project_root / PHASE2_FOLDER_NAME
    output_path = project_root / PHASE3_OUTPUT_NAME

    # 1) Index all original jobs by id from input_files JSON
    jobs_by_id = build_jobs_index_from_input_files(input_folder)

    # 2) Collect all apply-now rows from Phase 2 outputs
    apply_rows = read_phase2_apply_now_rows(phase2_folder)
    if not apply_rows:
        print("No apply now rows found. Nothing to do.")
        return

    # 3) Output columns: all Phase 2 columns + cleaned job description + title/company/apply_url
    base_fieldnames = list(apply_rows[0].keys())
    extra_cols = [
        "job_description",  # cleaned, no HTML
        "title",
        "company_name",
        "apply_url",
    ]
    fieldnames = base_fieldnames[:]
    for col in extra_cols:
        if col not in fieldnames:
            fieldnames.append(col)

    print(f"Phase 3: writing combined CSV to {output_path}")
    missing_ids = 0

    with output_path.open("w", encoding="utf-8", newline="") as f_out:
        writer = csv.DictWriter(f_out, fieldnames=fieldnames)
        writer.writeheader()

        for row in apply_rows:
            job_id = row.get(PHASE2_JOB_ID_COL)
            if not job_id:
                continue

            original = jobs_by_id.get(str(job_id))
            if not original:
                missing_ids += 1
                continue

            job_info = original.get(JSON_JOB_INFO_KEY, {}) or {}
            v5 = original.get(JSON_V5_KEY, {}) or {}

            raw_jd_html = job_info.get(JSON_JD_FIELD, "")
            cleaned_jd = strip_html(raw_jd_html)

            title = job_info.get(JSON_TITLE_FIELD, "")
            company_name = v5.get(JSON_COMPANY_FIELD, "")
            apply_url = original.get(JSON_APPLY_URL_FIELD, "")

            row["job_description"] = cleaned_jd
            row["title"] = title
            row["company_name"] = company_name
            row["apply_url"] = apply_url

            writer.writerow(row)

    print(f"Phase 3: done. Wrote {output_path}")
    if missing_ids:
        print(
            f"Warning: {missing_ids} apply-now rows had no matching job in input_files JSON."
        )


if __name__ == "__main__":
    main()
