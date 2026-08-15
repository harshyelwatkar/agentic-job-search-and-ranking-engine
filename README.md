# Agentic Job Search and Ranking Engine

An agentic job-search system that combines Vespa retrieval with query understanding, plan-aware candidate filtering, job-specific reranking, match-quality classification, and search explanations.

The system is designed to return relevant job opportunities while explicitly distinguishing between strong, partial, and weak matches instead of treating every retrieved document as equally suitable.

## Overview

```text
The search pipeline is:

User Query
↓
Query Planning
↓
Retrieval Strategy Selection
↓
Vespa Job Retrieval
↓
Plan-Aware Candidate Gating
↓
Job-Specific Reranking
↓
Match Quality Classification
↓
Search Explanation
↓
FastAPI
↓
Web UI
```

## Main Components

### agent.py

Builds a structured SearchPlan from a natural-language job query.

The plan can contain:

- role terms
- skills
- locations
- experience requirements
- entry-level / senior-level signals
- employment types
- retrieval mode
- gating mode
- matching requirements

### agent_search.py

Executes a SearchPlan.

Pipeline:

1. Retrieve candidates from Vespa.
2. Apply plan-aware gating.
3. Rerank eligible candidates.
4. Classify match quality.
5. Return ranked results.

### job_search.py

Provides the core Vespa job-search interface and converts Vespa hits into normalized job records.

### job_hybrid.py

Defines the current job-oriented Vespa application package and job schema.

### job_feed.py

Feeds the normalized/filtered job dataset into the jobs-clean Vespa instance.

## Ranking

The ranking/ package contains the job-specific ranking logic.

### query_parser.py

Extracts structured search intent from a user query.

Example:

Java Spring Boot developer

becomes:

- Role: java developer
- Skills: spring boot, java

Compound skills such as spring boot are normalized so that spring is not incorrectly counted as a separate requirement.

### job_ranker.py

Calculates job-match features and produces a Python-side reranked result set.

Features include:

- role/title compatibility
- skill coverage
- experience compatibility
- location compatibility
- employment compatibility
- Vespa retrieval relevance

### plan_gate.py

Filters candidates according to the generated search plan.

The gate prevents unrelated jobs from passing solely because they contain an isolated keyword or skill.

### match_quality.py

Classifies results as:

- strong
- partial
- weak

### search_explanation.py

Produces user-facing explanations containing:

- matched skills
- missing skills
- match quality
- search summary
- best available match

### test_local_ranking.py

Runs the ranking and gating logic locally without making Vespa requests.

This is intentionally used for regression testing before performing live Vespa searches.

## Job Data Pipeline

The local job corpus is built in stages:

candidate_jobs.jsonl
↓
normalize_jobs.py
↓
jobs.jsonl
↓
filter_jobs.py
↓
jobs_clean.jsonl
↓
job_feed.py
↓
Vespa jobs-clean instance

### candidate_jobs.jsonl

Raw extracted candidate job pages.

### jobs.jsonl

Normalized job records.

### jobs_clean.jsonl

Filtered job records selected for the job-search corpus.

## Web Interface

The web application is served through FastAPI.

### Backend

ui.py

Provides:

- /
- /api/health
- /api/search

### Frontend

```text
ui_assets/
├── index.html
├── app.js
└── styles.css
```

The interface displays:

- parsed search plan
- retrieval mode
- match quality
- matched skills
- missing skills
- ranking scores
- job metadata
- match explanations
- job links

## Local Development

Create/activate the environment and run the application with:

```bash
uv run uvicorn ui:app --reload
```

Then open:

```text
http://127.0.0.1:8000
```

Health check:

```bash
curl http://127.0.0.1:8000/api/health
```

Expected response:

```json
{
  "status": "ok",
  "service": "agentic-job-search"
}
```

## Local Regression Tests

The ranking and gating logic can be tested without contacting Vespa:

```bash
uv run python -m py_compile ranking/test_local_ranking.py
uv run python ranking/test_local_ranking.py
```

The test suite covers:

- query parsing
- role + skill gating
- partial skill matching
- strong matching
- entry-level queries
- remote constraints
- explanation generation

## Example Queries

Useful example searches include:

React Node.js full stack developer
Java Spring Boot developer
data engineer SQL
machine learning engineer
entry level software engineer
software engineer remote
senior Python backend AWS engineer remote

The system may intentionally return no eligible jobs when the available corpus does not contain a sufficiently trustworthy match.

This is preferred to returning an unrelated job simply because one keyword or skill overlaps.

## Project Structure

```text
.
├── agent.py
├── agent_search.py
├── deploy_jobs.py
├── job_feed.py
├── job_hybrid.py
├── job_search.py
├── job_data/
│   ├── candidate_jobs.jsonl
│   ├── extract_jobs.py
│   ├── filter_jobs.py
│   ├── jobs_clean.jsonl
│   ├── jobs.jsonl
│   └── normalize_jobs.py
├── ranking/
│   ├── evaluate_ranking.py
│   ├── __init__.py
│   ├── job_ranker.py
│   ├── match_quality.py
│   ├── plan_gate.py
│   ├── query_parser.py
│   ├── ranking_report_baseline.json
│   ├── search_explanation.py
│   ├── test_local_ranking.py
│   └── test_queries.json
├── ui.py
├── ui_assets/
│   ├── app.js
│   ├── index.html
│   └── styles.css
├── README.md
├── .gitignore
├── pyproject.toml
├── .python-version
└── uv.lock
```

## Validation Philosophy

The system separates:

1. Retrieval
2. Candidate eligibility
3. Ranking
4. Match-quality interpretation
5. User-facing explanation

This separation makes it possible to improve individual stages without making the entire search system dependent on one opaque score.

The project also includes an offline regression suite so ranking and gating changes can be tested without repeatedly querying Vespa.

## Current Evaluation Note

The file:

ranking/ranking_report_baseline.json

contains a baseline from an earlier ranking configuration.

It is retained as a historical comparison artifact and should not be treated as the final benchmark for the current ranking implementation.
