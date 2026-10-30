# RecruiterFlow Bot — Backend Developer Assignment

A backend service that ingests fictional candidate profiles and job openings, then ranks the best matches for each using a transparent, rule-based scoring algorithm. Built as a take-home assignment for the RecruiterFlow Engineering Internship.

## Technology Stack

| Component       | Choice                          |
|-----------------|---------------------------------|
| Language        | Python 3.12                     |
| Web framework   | FastAPI                         |
| Database        | SQLite (via Python's `sqlite3`) |
| Validation      | Pydantic                        |
| Testing         | pytest + FastAPI TestClient     |
| SQL             | Raw, hand-written (no ORM)      |

## Prerequisites

- Python 3.11 or newer
- pip

## Installation

```bash
# Clone the repository
git clone <repo-url>
cd recruiterflow-backend

# Create and activate a virtual environment (recommended)
python -m venv venv
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

## Database Initialization

Create (or recreate) the database with all seed data:

```bash
python -m scripts.init_db
```

Output:
```
Created database tables.
Seeded 15 candidates, 6 jobs, 27 unique skills.
Database created at: data/recruiterflow.db
```

The database is also auto-created on first API startup if it doesn't exist.

## Starting the API

```bash
python -m uvicorn app.main:app --reload
```

The API will be available at `http://127.0.0.1:8000`.  
Interactive Swagger docs are at `http://127.0.0.1:8000/docs`.

## API Endpoints

### `GET /jobs/{id}/matches`

Returns all candidates ranked by match score for the specified job.

**Example:**

```bash
curl http://127.0.0.1:8000/jobs/1/matches
```

**Response (abbreviated):**

```json
{
  "job_id": 1,
  "job_title": "Backend Detective",
  "matches": [
    {
      "candidate_id": 1,
      "candidate_name": "Sherlock H.",
      "score": 95.0,
      "matched_skills": ["deduction", "forensics", "pattern-recognition"],
      "experience_years": 8,
      "meets_experience": true,
      "availability": "Immediate",
      "skill_score": 60.0,
      "experience_score": 25.0,
      "trait_score": 5.0,
      "availability_score": 5.0,
      "reason": "Matched 3/3 required skills (deduction, forensics, pattern-recognition). Meets experience requirement (8 >= 3 yrs). Available immediately."
    },
    {
      "candidate_id": 9,
      "candidate_name": "Sheldon C.",
      "score": 50.0,
      "matched_skills": ["pattern-recognition"],
      "experience_years": 9,
      "meets_experience": true,
      "availability": "Immediate",
      "skill_score": 20.0,
      "experience_score": 25.0,
      "trait_score": 0.0,
      "availability_score": 5.0,
      "reason": "Matched 1/3 required skills (pattern-recognition). Meets experience requirement (9 >= 3 yrs). Available immediately."
    }
  ]
}
```

### `GET /candidates/{id}/matches`

Returns all jobs ranked by match score for the specified candidate.

**Example:**

```bash
curl http://127.0.0.1:8000/candidates/1/matches
```

**Response (abbreviated):**

```json
{
  "candidate_id": 1,
  "candidate_name": "Sherlock H.",
  "matches": [
    {
      "job_id": 1,
      "job_title": "Backend Detective",
      "score": 95.0,
      "matched_skills": ["deduction", "forensics", "pattern-recognition"],
      "matched_skills_count": 3,
      "min_experience": 3,
      "meets_experience": true,
      "skill_score": 60.0,
      "experience_score": 25.0,
      "trait_score": 5.0,
      "availability_score": 5.0,
      "reason": "Matched 3/3 required skills (deduction, forensics, pattern-recognition). Meets experience requirement (8 >= 3 yrs). Available immediately."
    }
  ]
}
```

### Error Handling

Nonexistent IDs return HTTP 404:

```bash
curl http://127.0.0.1:8000/jobs/999/matches
# {"detail": "Job with id 999 not found"}
```

## Running Tests

```bash
python -m pytest tests/ -v
```

All 61 tests should pass, covering:
- Database seeding and integrity (CHECK constraints, FK enforcement)
- Score computation with known inputs
- Edge cases (empty skills, zero experience, case sensitivity)
- Deterministic ranking and tie-breaking
- Both API endpoints (valid requests, 404 errors, response structure)
- All 5 SQL Detective queries against expected results

## Running the SQL Detective Queries


The file `sql/sql_detective.sql` is self-contained — it includes the schema, seed data, and all 5 queries. To run it, use the SQLite command-line tool:

```bash
sqlite3 :memory: < sql/sql_detective.sql
```

This command requires the SQLite command-line tool to be installed. Alternatively, open the file in an SQLite-compatible SQL client. Each query is preceded by a comment identifying the question number.

## Matching Algorithm

### Score Scale: 0–100

The total match score is composed of four weighted components:

| Component          | Max Points | Calculation                                               |
|--------------------|------------|-----------------------------------------------------------|
| **Skill match**    | 60         | `(matched skills / required skills) × 60`                 |
| **Experience fit** | 25         | Full 25 if `candidate_exp >= min_exp`, else proportional   |
| **Trait/culture**  | 10         | `(matching traits / culture keywords) × 10`               |
| **Availability**   | 5          | Immediate = 5, 2 weeks = 3, Not looking = 0               |

### Normalization

All skill and keyword comparisons use exact normalized string matching: trimmed whitespace, lowercased. Each required skill is counted at most once. There is no semantic, fuzzy, or AI-based matching.

### Experience Fit Details

- If a job has `min_experience = 0`, the candidate gets full 25 points (no division by zero).
- If `candidate_experience >= min_experience`, the candidate gets full 25 points.
- Otherwise: `(candidate_experience / min_experience) × 25` (proportional penalty).

### Why Some Matches Score Below 100

Even when a candidate matches all required skills (60 pts) and meets the experience minimum (25 pts), the maximum from those two components is 85. The remaining 15 points depend on:
- Whether the candidate's traits overlap with the job's culture keywords (up to 10 pts)
- The candidate's availability status (up to 5 pts)

A candidate who is "Not looking" and has no trait overlap with culture keywords would score at most 85.

### Tie-Breaking Rules

**For `GET /jobs/{id}/matches`** (ranking candidates):
1. Score descending
2. Candidate experience descending (more experienced first)
3. Candidate name ascending (alphabetical)
4. Candidate ID ascending (deterministic final tiebreaker)

**For `GET /candidates/{id}/matches`** (ranking jobs):
1. Score descending
2. Number of matched skills descending (more matches first)
3. Job title ascending (alphabetical)
4. Job ID ascending (deterministic final tiebreaker)

### Handling of "Not Looking" Candidates

Candidates with availability "Not looking" are still included in results — they simply receive 0 availability bonus points. Their availability status is visible in the response so the caller can filter or flag them as needed.

## Database Design

### Entity-Relationship Overview

```
candidates ──┬── candidate_skills ──┬── skills ──┬── job_skills ──┬── jobs
             │                      │            │               │
             └── candidate_traits   └────────────┘               └── job_culture_keywords
```

### Tables

| Table                  | Purpose                                         |
|------------------------|-------------------------------------------------|
| `candidates`           | Name, experience, availability, quirk            |
| `jobs`                 | Title, min experience, tagline                   |
| `skills`               | Normalized skill names (shared lookup)           |
| `candidate_skills`     | Many-to-many: candidate ↔ skill                  |
| `job_skills`           | Many-to-many: job ↔ skill                        |
| `candidate_traits`     | Many-to-many: candidate ↔ trait (text)           |
| `job_culture_keywords` | Many-to-many: job ↔ culture keyword (text)       |


### Database Design Decisions

1. **Shared Skills Table:** Candidates and jobs can have the same skills, so I used one `skills` table instead of storing the same skill multiple times. Junction tables connect skills to candidates and jobs, making it easier to find matching skills using SQL JOINs.

2. **Traits and Culture Keywords:** I stored candidate traits and job culture keywords as text in junction tables. For this project, separate lookup tables for these values were not necessary, so this approach keeps the database simpler.

3. **CHECK Constraints:** I added constraints to prevent invalid data, such as negative experience values. The availability field is also restricted to `'Immediate'`, `'2 weeks'`, or `'Not looking'`.

4. **Foreign Keys and Indexes:** I enabled `PRAGMA foreign_keys = ON` for every database connection to maintain relationships between tables. I also added indexes to foreign-key columns used in JOINs to help queries run efficiently.

## SQL Detective Challenge

The file `sql/sql_detective.sql` contains:

| Question | Description                                               | Key Technique                                  |
|----------|-----------------------------------------------------------|------------------------------------------------|
| Q1       | Open job postings with recruiter names                    | JOIN + WHERE filter                            |
| Q2       | Final-stage applicant count per job (including zeros)     | LEFT JOIN with condition in ON clause          |
| Q3       | People who applied to more than one job                   | LOWER(email) to handle duplicate records       |
| Q4       | Final-stage conversion rate (≥3 interviews)               | HAVING + NULLIF for zero-division safety       |
| Q5       | Top recruiter per department (bonus)                      | CTE + RANK() window function                   |

### Q3 Note on Duplicates
Ananya Rao appears twice in the data (IDs 1 and 2) with emails that differ only in capitalization (`ananya.rao@mail.com` vs `Ananya.Rao@mail.com`). The query normalizes emails with `LOWER()` to correctly identify her as one person who applied to two different jobs. The query uses the available interview records to identify the jobs associated with each person, since the dataset does not provide a separate applications table.

### Q5 Tie-Handling
`RANK()` is used so that if two recruiters tie for the most placements in a department, both are returned. Departments with zero successful placements (e.g., Infrastructure) do not appear.

## Project Structure

```
recruiterflow-backend/
├── app/
│   ├── __init__.py
│   ├── main.py            # FastAPI app with lifespan startup
│   ├── database.py         # Connection, schema, seed data (raw SQL)
│   ├── models.py           # Pydantic response models
│   ├── matching.py         # Scoring algorithm + ranking queries
│   └── routes/
│       ├── __init__.py
│       └── matches.py      # API endpoint handlers
├── scripts/
│   └── init_db.py          # Standalone DB initialization script
├── sql/
│   └── sql_detective.sql   # SQL Detective Challenge (5 queries)
├── tests/
│   ├── __init__.py
│   ├── conftest.py         # Shared pytest fixtures
│   ├── test_matching.py    # Algorithm + seeding tests
│   ├── test_api.py         # API endpoint tests
│   └── test_sql_detective.py # SQL query verification tests
├── data/
│   └── .gitkeep            # Generated .db files live here (gitignored)
├── requirements.txt
├── .gitignore
└── README.md
```

## Limitations and Improvements


### Current Limitations

- **No Pagination:** Both endpoints return all matching candidates or jobs in one response. This works for the current dataset, but pagination would be useful if the number of records increases.

- **No Caching:** The match scores are calculated again whenever a request is made. Caching could help avoid repeated calculations if the same results are requested frequently.

- **SQLite Concurrency:** The application uses SQLite, which is suitable for this project but may not be the best choice for handling a large number of simultaneous write requests in a production environment.

- **No API for Adding New Records:** The initial candidate and job data is loaded through the seed script, as permitted by the assignment. POST endpoints could be added in the future to allow new candidates and jobs to be created through the API.

- **Exact Trait Matching:** Candidate traits and job culture keywords are compared using exact normalized string matching. For example, "calm" and "calm-under-pressure" are treated as different values, so related terms may not match.

### What I Would Improve With More Time

- **Pagination and Filtering:** Add pagination so recruiters can view matching candidates in smaller batches. Also allow filtering by minimum match score and availability.

- **Candidate and Job Creation:** Add POST endpoints so recruiters can add new candidates and jobs through the API instead of relying only on the initial sample data.

- **Configurable Score Weights:** Allow recruiters to adjust the importance of skills, experience, culture fit, and availability depending on the job requirements.

- **Database Connection Management:** Explore better ways to manage database connections if the application needs to handle more users and requests.

- **Bonus for Extra Skills:** Give candidates additional points for relevant skills beyond the job requirements, while keeping the overall score capped at 100.

- **Improved Trait Matching:** Support similar terms when comparing candidate traits with job culture keywords. For example, "calm" and "calm-under-pressure" could be treated as related traits.

## AI Tools Disclosure

I used ChatGPT and Google Gemini through the Antigravity IDE while working on this project. I was involved in understanding the requirements, deciding how to approach the problem, developing the backend, improving the code, and testing the application.

Throughout the project, I worked on turning the assignment requirements into a working application, including the API endpoints, database operations, and candidate-job matching functionality. ChatGPT and Gemini helped me work through implementation challenges, refine the code, troubleshoot errors, and improve the overall solution. They also assisted with understanding the assignment PDF, preparing the sample data, and developing test cases.

For the SQL Detective section, I was involved in writing the queries and used AI assistance to refine them. I ran the queries and checked their results to make sure they answered the assignment questions correctly.

I tested the API endpoints, checked how the application handled errors, and verified the SQL query results. All 61 automated tests passed. Working on this project helped me apply what I learned about backend development, databases, SQL, candidate-job matching, and API testing.

Overall, I used ChatGPT and Gemini as tools to help me develop and improve the project, while actively participating in the coding, problem-solving, testing, and validation process.
