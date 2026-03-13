# Hiring Café JSON → CSV Converter

This project converts Hiring Café JSON job responses into clean, compact CSV files that can be used as input to an LLM, together with a user’s resume, to filter and rank job openings.

---

## Purpose

The main goal is to transform raw job posting JSON into token‑efficient CSV batches that are easy for an LLM to consume when matching jobs to a candidate’s resume.

---

## Features

- Read multiple JSON response files from the `input_files` directory.
- Extract only the required fields from each job (title, category, level, tools, summary, etc.).
- Strip HTML tags from job descriptions to reduce noise and token usage.
- Aggregate all jobs and write multiple CSV files, with up to **100 job openings per CSV**.

---

## How it works

1. Place raw Hiring Café JSON response files into `input_files/`.
2. Run the converter script.
3. The script:
   - Parses each JSON file.
   - Picks only the selected fields from each job.
   - Cleans job descriptions by removing HTML tags.
   - Groups all jobs into batches of 100 and writes them as separate CSV files in `output/`.
4. Use these CSV files as structured input to an LLM alongside a user’s resume to score and filter job matches based on keyword and skill alignment.

---

## Project structure

```text
project-root/
  input_files/    # JSON response files from Hiring Café
  output/         # Generated CSV files (100 jobs per CSV)
  src/
    main.py       # JSON → CSV conversion logic
  README.md
  .gitignore
```
