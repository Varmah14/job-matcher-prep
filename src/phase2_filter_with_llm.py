import csv
import json
import os
import time
from typing import List, Dict, Any

from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()  # NEW: loads .env from project root by default


api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    raise RuntimeError("GEMINI_API_KEY is not set. Check your .env file.")
client = genai.Client(api_key=api_key)


# client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])


# ---------- Config ----------

BATCH_SLEEP_SECONDS = 0  # delay between LLM calls
PHASE1_FOLDER_NAME = "output_phase1_structured"
PHASE2_FOLDER_NAME = "output_phase2_classified"
RESUME_PATH = "resume.txt"
MODEL_NAME = "gemini-2.5-flash"  # or another Gemini model
# MODEL_NAME = "gemini-3.1-pro-preview"  # or another Gemini model
# gemini-2.5-flash


# ---------- IO helpers ----------


CLASS_ORDER = {
    "apply now": 0,
    "consider": 1,
    "skip": 2,
    None: 3,
    "": 3,
}


def load_resume_text(project_root: str) -> str:
    resume_path = os.path.join(project_root, RESUME_PATH)
    with open(resume_path, "r", encoding="utf-8") as f:
        return f.read().strip()


def read_jobs_from_csv(path: str) -> List[Dict[str, Any]]:
    with open(path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return list(reader)


def write_classified_csv(
    input_csv_path: str,
    jobs: List[Dict[str, Any]],
    classifications: Dict[str, Dict[str, Any]],
    output_folder: str,
) -> None:
    os.makedirs(output_folder, exist_ok=True)

    fieldnames = list(jobs[0].keys()) + ["classification", "score", "reason"]

    filename = os.path.basename(input_csv_path)
    base, ext = os.path.splitext(filename)
    out_name = base + "_classified" + ext
    out_path = os.path.join(output_folder, out_name)

    jobs_sorted = sort_jobs_by_classification(jobs, classifications)

    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for job in jobs_sorted:
            job_id = job.get("id")
            cls = classifications.get(job_id, {})
            row = {
                **job,
                "classification": cls.get("classification"),
                "score": cls.get("score"),
                "reason": cls.get("reason"),
            }
            writer.writerow(row)

    print(f"  → Wrote classified CSV: {out_path}")


# def write_classified_csv(...):
#     os.makedirs(output_folder, exist_ok=True)
#     fieldnames = list(jobs[0].keys()) + ["classification", "score", "reason"]

#     filename = os.path.basename(input_csv_path)
#     base, ext = os.path.splitext(filename)
#     out_name = base + "_classified" + ext
#     out_path = os.path.join(output_folder, out_name)

#     # sort jobs by classification
#     jobs_sorted = sort_jobs_by_classification(jobs, classifications)

#     with open(out_path, "w", newline="", encoding="utf-8") as f:
#         writer = csv.DictWriter(f, fieldnames=fieldnames)
#         writer.writeheader()

#         for job in jobs_sorted:
#             job_id = job.get("id")
#             cls = classifications.get(job_id, {})
#             row = {
#                 **job,
#                 "classification": cls.get("classification"),
#                 "score": cls.get("score"),
#                 "reason": cls.get("reason"),
#             }
#             writer.writerow(row)


def sort_jobs_by_classification(
    jobs: List[Dict[str, Any]],
    classifications: Dict[str, Dict[str, Any]],
) -> List[Dict[str, Any]]:
    def sort_key(job: Dict[str, Any]):
        job_id = job.get("id")
        cls = classifications.get(job_id, {})
        label = (cls.get("classification") or "").strip().lower()
        return CLASS_ORDER.get(label, 3)

    return sorted(jobs, key=sort_key)


# ---------- LLM prompt + call (Gemini) ----------


def build_llm_prompt(resume_text: str, jobs: List[Dict[str, Any]]) -> str:
    header = list(jobs[0].keys())
    lines = [",".join(header)]
    for job in jobs:
        row = [
            str(job.get(col, "")).replace("\n", " ").replace(",", ";") for col in header
        ]
        lines.append(",".join(row))
    jobs_csv_block = "\n".join(lines)

    prompt = f"""
You are an expert job-matching assistant.

Given the candidate's resume and a table of job openings, classify EACH job into:
- "apply now"
- "consider"
- "skip"

Also provide:
- a numeric fit score between 0.0 and 1.0 (higher is better)
- - a very short reason (max 15 words).

Return ONLY valid JSON in the following format:
[
  {{
    "id": "<job id>",
    "classification": "<apply now|consider|skip>",
    "score": 0.0,
    "reason": "<short reason>"
  }},
  ...
]

Candidate resume:
\"\"\"text
{resume_text}
\"\"\"

Jobs (CSV with header row):
\"\"\"csv
{jobs_csv_block}
\"\"\"
"""
    return prompt.strip()


# global Gemini client (uses GEMINI_API_KEY from env)
client = genai.Client()


def call_llm_for_batch(
    resume_text: str, jobs: List[Dict[str, Any]]
) -> Dict[str, Dict[str, Any]]:
    prompt = build_llm_prompt(resume_text, jobs)

    response = client.models.generate_content(
        model=MODEL_NAME,
        contents=prompt,
        config=types.GenerateContentConfig(response_mime_type="application/json"),
    )

    try:
        data = json.loads(response.text)
    except json.JSONDecodeError as e:
        print("WARNING: Gemini did not return valid JSON for this batch.")
        print("Error:", e)
        print("Partial response (first 500 chars):")
        print(response.text[:500])
        # Return empty classifications so this batch is effectively skipped
        return {}

    if not isinstance(data, list):
        raise RuntimeError(f"Unexpected JSON shape from Gemini: {data}")

    classifications: Dict[str, Dict[str, Any]] = {}
    for item in data:
        job_id = item.get("id")
        if not job_id:
            continue
        classifications[job_id] = {
            "classification": item.get("classification"),
            "score": item.get("score"),
            "reason": item.get("reason"),
        }

    return classifications


# ---------- Batch driver ----------


def process_all_batches():
    project_root = os.path.dirname(os.path.dirname(__file__))
    phase1_folder = os.path.join(project_root, PHASE1_FOLDER_NAME)
    phase2_folder = os.path.join(project_root, PHASE2_FOLDER_NAME)

    resume_text = load_resume_text(project_root)
    print("Loaded resume from:", os.path.join(project_root, RESUME_PATH))

    batch_files = sorted(f for f in os.listdir(phase1_folder) if f.endswith(".csv"))
    if not batch_files:
        print("No Phase 1 CSV files found.")
        return

    print(f"Found {len(batch_files)} Phase 1 CSV batch file(s): {batch_files}")

    for i, filename in enumerate(batch_files, start=1):
        path = os.path.join(phase1_folder, filename)
        print(f"\n[{i}/{len(batch_files)}] Processing {filename}...")

        jobs = read_jobs_from_csv(path)
        print(f"  Loaded {len(jobs)} jobs from batch.")

        classifications = call_llm_for_batch(resume_text, jobs)
        write_classified_csv(path, jobs, classifications, phase2_folder)

        if i < len(batch_files):
            print(f"  Sleeping {BATCH_SLEEP_SECONDS} seconds before next batch...")
            time.sleep(BATCH_SLEEP_SECONDS)


def main():
    process_all_batches()


if __name__ == "__main__":
    main()
