def deduplicate_jobs(jobs):
    """
    Remove duplicate job postings based on a single composite key
    that always includes id (if present) plus key attributes.
    """
    seen = set()
    unique_jobs = []

    for job in jobs:
        key = (
            (job.get("id") or "").strip().lower(),
            (job.get("core_job_title") or "").strip().lower(),
            (job.get("company_name") or "").strip().lower(),
            (job.get("job_category") or "").strip().lower(),
            (job.get("seniority_level") or "").strip().lower(),
        )

        if key in seen:
            continue

        seen.add(key)
        unique_jobs.append(job)

    print(f"Deduplicated jobs: kept {len(unique_jobs)} of {len(jobs)}")
    return unique_jobs
