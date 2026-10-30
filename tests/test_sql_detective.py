"""
Tests for the SQL Detective Challenge queries.

Each test creates a fresh database with the hiring-ops schema and seed
data, runs the corresponding query from sql_detective.sql, and verifies
the results against hand-checked expected values.
"""

import sqlite3
from pathlib import Path


# ---------------------------------------------------------------------------
# Helper: read individual queries from the SQL file
# ---------------------------------------------------------------------------

def _load_queries() -> dict[int, str]:
    """
    Parse sql_detective.sql and return a dict mapping question number (1-5)
    to the SQL query string for that question.

    Strategy: split the file on ``-- QUESTION `` markers, then for each
    chunk skip the number line and all comment / separator lines to
    isolate the actual SQL.
    """
    sql_path = Path(__file__).resolve().parent.parent / "sql" / "sql_detective.sql"
    text = sql_path.read_text(encoding="utf-8")

    queries: dict[int, str] = {}
    parts = text.split("-- QUESTION ")
    for part in parts[1:]:  # skip everything before the first marker
        # The first token is the question number (e.g. "1" or "5 (Bonus)")
        first_line = part.split("\n", 1)[0].strip()
        q_num = int(first_line[0])  # always a single digit

        lines = part.split("\n")[1:]  # drop the number line
        sql_lines: list[str] = []
        collecting = False
        for line in lines:
            stripped = line.strip()
            # Skip comment and separator lines before the SQL
            if not collecting:
                if stripped == "" or stripped.startswith("--"):
                    continue
                collecting = True
            # Stop if we hit the next separator block
            if stripped.startswith("-- ====="):
                break
            sql_lines.append(line)

        query = "\n".join(sql_lines).strip().rstrip(";") + ";"
        queries[q_num] = query

    return queries


QUERIES = _load_queries()


# ---------------------------------------------------------------------------
# Question 1: Open job postings with recruiter names
# ---------------------------------------------------------------------------

class TestQuestion1:
    def test_returns_only_open_postings(self, detective_db: sqlite3.Connection):
        rows = detective_db.execute(QUERIES[1]).fetchall()
        job_ids = {r["job_id"] for r in rows}
        # Open jobs: 1, 2, 4, 5 (not 3=closed, 6=on_hold, 7=closed)
        assert job_ids == {1, 2, 4, 5}

    def test_recruiter_names_correct(self, detective_db: sqlite3.Connection):
        rows = detective_db.execute(QUERIES[1]).fetchall()
        id_to_recruiter = {r["job_id"]: r["recruiter_name"] for r in rows}
        assert id_to_recruiter[1] == "Priya Shah"
        assert id_to_recruiter[2] == "Daniel Ortiz"
        assert id_to_recruiter[4] == "Priya Shah"
        assert id_to_recruiter[5] == "Wei Zhang"


# ---------------------------------------------------------------------------
# Question 2: Final-stage applicant counts per job (including zeros)
# ---------------------------------------------------------------------------

class TestQuestion2:
    def test_all_seven_jobs_present(self, detective_db: sqlite3.Connection):
        rows = detective_db.execute(QUERIES[2]).fetchall()
        assert len(rows) == 7, "All 7 jobs should appear, including those with 0"

    def test_counts_correct(self, detective_db: sqlite3.Connection):
        rows = detective_db.execute(QUERIES[2]).fetchall()
        counts = {r["job_id"]: r["final_stage_applicants"] for r in rows}
        # Job 1: applicants 1 (passed) and 4 (failed) → 2
        assert counts[1] == 2
        # Job 2: applicants 5 (passed) and 6 (failed) → 2
        assert counts[2] == 2
        # Job 3: applicant 3 (passed) → 1
        assert counts[3] == 1
        # Job 4: applicants 8 (passed) and 9 (passed) → 2
        assert counts[4] == 2
        # Job 5: no Final interviews → 0
        assert counts[5] == 0
        # Job 6: no Final interviews → 0
        assert counts[6] == 0
        # Job 7: applicants 11 (passed) and 6 (failed) → 2
        assert counts[7] == 2


# ---------------------------------------------------------------------------
# Question 3: People who applied to more than one job
# ---------------------------------------------------------------------------

class TestQuestion3:
    def test_correct_people_found(self, detective_db: sqlite3.Connection):
        rows = detective_db.execute(QUERIES[3]).fetchall()
        emails = {r["normalized_email"] for r in rows}
        # Ananya Rao (ids 1,2 same person) → jobs 1,4
        # Ben Turner (id 3) → jobs 1,3
        # Elena Popescu (id 6) → jobs 2,7
        assert "ananya.rao@mail.com" in emails
        assert "ben.turner@mail.com" in emails
        assert "elena.popescu@mail.com" in emails
        assert len(emails) == 3

    def test_ananya_duplicate_handled(self, detective_db: sqlite3.Connection):
        """Ananya Rao has 2 applicant records with different-case emails."""
        rows = detective_db.execute(QUERIES[3]).fetchall()
        ananya = [r for r in rows if r["normalized_email"] == "ananya.rao@mail.com"]
        assert len(ananya) == 1
        assert ananya[0]["jobs_applied_to"] == 2

    def test_ben_applied_to_two_jobs(self, detective_db: sqlite3.Connection):
        rows = detective_db.execute(QUERIES[3]).fetchall()
        ben = [r for r in rows if r["normalized_email"] == "ben.turner@mail.com"]
        assert len(ben) == 1
        assert ben[0]["jobs_applied_to"] == 2


# ---------------------------------------------------------------------------
# Question 4: Final-stage conversion rate (>= 3 Final interviews)
# ---------------------------------------------------------------------------

class TestQuestion4:
    def test_only_qualifying_recruiters(self, detective_db: sqlite3.Connection):
        rows = detective_db.execute(QUERIES[4]).fetchall()
        names = {r["recruiter_name"] for r in rows}
        # Priya Shah: 4 Final interviews (jobs 1+4), Daniel Ortiz: 4 Final (jobs 2+7)
        # Others have < 3 Final interviews
        assert names == {"Priya Shah", "Daniel Ortiz"}

    def test_priya_conversion_rate(self, detective_db: sqlite3.Connection):
        rows = detective_db.execute(QUERIES[4]).fetchall()
        priya = [r for r in rows if r["recruiter_name"] == "Priya Shah"][0]
        # Priya: 3 passed / 4 total = 0.75
        assert priya["total_final"] == 4
        assert priya["passed_final"] == 3
        assert priya["conversion_rate"] == 0.75

    def test_daniel_conversion_rate(self, detective_db: sqlite3.Connection):
        rows = detective_db.execute(QUERIES[4]).fetchall()
        daniel = [r for r in rows if r["recruiter_name"] == "Daniel Ortiz"][0]
        # Daniel: 2 passed / 4 total = 0.50
        assert daniel["total_final"] == 4
        assert daniel["passed_final"] == 2
        assert daniel["conversion_rate"] == 0.5


# ---------------------------------------------------------------------------
# Question 5 (Bonus): Most successful recruiter per department
# ---------------------------------------------------------------------------

class TestQuestion5:
    def test_engineering_winner(self, detective_db: sqlite3.Connection):
        rows = detective_db.execute(QUERIES[5]).fetchall()
        eng = [r for r in rows if r["department"] == "Engineering"]
        # Priya Shah: 3 passed Final (jobs 1+4), Daniel Ortiz: 2 (jobs 2+7)
        assert len(eng) == 1
        assert eng[0]["recruiter_name"] == "Priya Shah"
        assert eng[0]["successful_placements"] == 3

    def test_data_winner(self, detective_db: sqlite3.Connection):
        rows = detective_db.execute(QUERIES[5]).fetchall()
        data = [r for r in rows if r["department"] == "Data"]
        # Fatima Al-Sayed: 1 passed Final (job 3)
        assert len(data) == 1
        assert data[0]["recruiter_name"] == "Fatima Al-Sayed"
        assert data[0]["successful_placements"] == 1

    def test_infrastructure_not_present(self, detective_db: sqlite3.Connection):
        """Infrastructure has 0 passed Final interviews, so no winner."""
        rows = detective_db.execute(QUERIES[5]).fetchall()
        infra = [r for r in rows if r["department"] == "Infrastructure"]
        assert len(infra) == 0
