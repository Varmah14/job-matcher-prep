# Hiring Café Job Matcher – Phase 1 (JSON → Structured CSV)

This project is part of a 4‑phase personal job‑matching pipeline. Phase 1 takes raw Hiring Café JSON responses and converts them into compact, deduplicated CSV batches ready to be scored by an LLM in later phases.

---

## Overview of the 4 Phases

1. **Phase 1 – JSON → CSV (this repo/script)**
   - Read raw Hiring Café JSON files.
   - Extract compact structured fields (no full job description).
   - Deduplicate jobs.
   - Write batched CSVs (100 jobs per file) for LLM screening.

2. **Phase 2 – Filter CSV with LLM**
   - Use an LLM with your resume + Phase‑1 CSVs.
   - Classify each job: `apply now`, `consider`, or `skip`, plus a score and reason.
   - Save classified CSVs.

3. **Phase 3 – Add JD for high‑match jobs**
   - Take high‑match jobs (e.g., `apply now`).
   - Re‑scan original JSON to pull full job descriptions.
   - Produce enriched CSVs with JD text for shortlisted jobs.

4. **Phase 4 – Final job list with LLM**
   - Use an LLM on the enriched CSV + resume.
   - Generate final scores, explanations, tailored resume bullets, and cover‑letter snippets.

This README focuses on **Phase 1**.

---

## Phase 1 – Goal

Turn raw Hiring Café JSON responses into **token‑efficient, structured CSV batches** that:

- Omit long job descriptions (JD) to keep prompts small.
- Include the most relevant structured fields for resume–job matching.
- Are deduplicated and limited to 100 jobs per file for easy batching into an LLM.

---

## Project Structure

```text
job-matcher-prep/
  input_files/                 # Raw Hiring Café JSON files (input)
  output_phase1_structured/    # Phase-1 CSV batches (output)
  src/
    __init__.py
    main.py                    # Phase-1 pipeline: JSON → CSV
    deduplication.py           # Deduplication logic
  README.md
```
