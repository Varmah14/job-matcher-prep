import json
import csv
import os
from html.parser import HTMLParser
from math import ceil


class HTMLStripper(HTMLParser):
    def __init__(self):
        super().__init__()
        self.text = []

    def handle_data(self, data):
        self.text.append(data)

    def get_text(self):
        return " ".join(self.text).strip()


def strip_html(html_string):
    if not html_string:
        return None
    stripper = HTMLStripper()
    stripper.feed(html_string)
    return stripper.get_text()


def pick_job_fields(data):
    results = data.get("results", [])
    picked = []

    for job in results:
        v5 = job.get("v5_processed_job_data", {})
        job_info = job.get("job_information", {})

        picked.append(
            {
                "core_job_title": v5.get("core_job_title"),
                "job_category": v5.get("job_category"),
                "seniority_level": v5.get("seniority_level"),
                "role_type": v5.get("role_type"),
                "associates_degree_requirement": v5.get(
                    "associates_degree_requirement"
                ),
                "associates_degree_fields_of_study": ", ".join(
                    v5.get("associates_degree_fields_of_study") or []
                ),
                "bachelors_degree_requirement": v5.get("bachelors_degree_requirement"),
                "bachelors_degree_fields_of_study": ", ".join(
                    v5.get("bachelors_degree_fields_of_study") or []
                ),
                "masters_degree_requirement": v5.get("masters_degree_requirement"),
                "masters_degree_fields_of_study": ", ".join(
                    v5.get("masters_degree_fields_of_study") or []
                ),
                "doctorate_degree_requirement": v5.get("doctorate_degree_requirement"),
                "doctorate_degree_fields_of_study": ", ".join(
                    v5.get("doctorate_degree_fields_of_study") or []
                ),
                "min_industry_and_role_yoe": v5.get("min_industry_and_role_yoe"),
                "min_management_and_leadership_yoe": v5.get(
                    "min_management_and_leadership_yoe"
                ),
                "requirements_summary": v5.get("requirements_summary"),
                "technical_tools": ", ".join(v5.get("technical_tools") or []),
                "role_activities": ", ".join(v5.get("role_activities") or []),
                "description": strip_html(job_info.get("description")),
                "company_name": v5.get("company_name"),
            }
        )

    return picked


def load_all_jobs(input_folder):
    all_jobs = []

    json_files = [f for f in os.listdir(input_folder) if f.endswith(".json")]
    if not json_files:
        print("No JSON files found in the folder.")
        return []

    print(f"Found {len(json_files)} file(s): {json_files}")

    for filename in json_files:
        filepath = os.path.join(input_folder, filename)
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
            jobs = pick_job_fields(data)
            all_jobs.extend(jobs)
            print(f"  ✓ {filename} → {len(jobs)} jobs")
        except Exception as e:
            print(f"  ✗ {filename} → Error: {e}")

    print(f"\nTotal jobs loaded: {len(all_jobs)}")
    return all_jobs


def write_batched_csvs(jobs, output_folder, batch_size=100, base_name="jobs_batch"):
    if not jobs:
        print("No jobs to write.")
        return

    os.makedirs(output_folder, exist_ok=True)

    fieldnames = [
        "core_job_title",
        "job_category",
        "seniority_level",
        "role_type",
        "associates_degree_requirement",
        "associates_degree_fields_of_study",
        "bachelors_degree_requirement",
        "bachelors_degree_fields_of_study",
        "masters_degree_requirement",
        "masters_degree_fields_of_study",
        "doctorate_degree_requirement",
        "doctorate_degree_fields_of_study",
        "min_industry_and_role_yoe",
        "min_management_and_leadership_yoe",
        "requirements_summary",
        "technical_tools",
        "role_activities",
        "description",
        "company_name",
    ]

    total = len(jobs)
    num_batches = ceil(total / batch_size)
    print(
        f"Writing {total} jobs into {num_batches} CSV file(s) with batch_size={batch_size}."
    )

    for i in range(num_batches):
        start = i * batch_size
        end = start + batch_size
        batch_jobs = jobs[start:end]

        filename = f"{base_name}_{i+1:02d}.csv"
        out_path = os.path.join(output_folder, filename)

        with open(out_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(batch_jobs)

        print(f"  → {out_path} ({len(batch_jobs)} jobs)")


def main():
    input_folder = os.path.join(os.path.dirname(__file__), "..", "input_files")
    output_folder = os.path.join(os.path.dirname(__file__), "..", "output")

    jobs = load_all_jobs(input_folder)
    write_batched_csvs(jobs, output_folder, batch_size=100, base_name="jobs")


if __name__ == "__main__":
    main()
