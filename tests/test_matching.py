"""
Tests for the matching algorithm and database seeding.

Covers:
    - Database initialization and seed-data integrity
    - Score computation with known inputs
    - Edge cases: empty skills, zero experience, all weights
    - Deterministic tie-breaking order
"""

import sqlite3

from app.database import get_connection, init_db, seed_db
from app.matching import compute_match_score, get_candidates_for_job, get_jobs_for_candidate


# ===================================================================
# Database seeding tests
# ===================================================================

class TestDatabaseSeeding:
    """Verify that init_db + seed_db load the correct data."""

    def test_candidate_count(self, test_db: sqlite3.Connection):
        count = test_db.execute("SELECT COUNT(*) AS cnt FROM candidates").fetchone()["cnt"]
        assert count == 15, f"Expected 15 candidates, got {count}"

    def test_job_count(self, test_db: sqlite3.Connection):
        count = test_db.execute("SELECT COUNT(*) AS cnt FROM jobs").fetchone()["cnt"]
        assert count == 6, f"Expected 6 jobs, got {count}"

    def test_skills_are_normalized(self, test_db: sqlite3.Connection):
        """All skill names should be lowercase and trimmed."""
        rows = test_db.execute("SELECT name FROM skills").fetchall()
        for row in rows:
            assert row["name"] == row["name"].strip().lower(), (
                f"Skill not normalized: '{row['name']}'"
            )

    def test_sherlock_skills(self, test_db: sqlite3.Connection):
        """Sherlock H. should have exactly 3 specific skills."""
        rows = test_db.execute(
            "SELECT s.name FROM candidate_skills cs "
            "JOIN skills s ON cs.skill_id = s.id "
            "JOIN candidates c ON cs.candidate_id = c.id "
            "WHERE c.name = 'Sherlock H.' ORDER BY s.name"
        ).fetchall()
        skills = [r["name"] for r in rows]
        assert skills == ["deduction", "forensics", "pattern-recognition"]

    def test_backend_detective_skills(self, test_db: sqlite3.Connection):
        """Backend Detective job should require deduction, pattern-recognition, forensics."""
        rows = test_db.execute(
            "SELECT s.name FROM job_skills js "
            "JOIN skills s ON js.skill_id = s.id "
            "JOIN jobs j ON js.job_id = j.id "
            "WHERE j.title = 'Backend Detective' ORDER BY s.name"
        ).fetchall()
        skills = [r["name"] for r in rows]
        assert skills == ["deduction", "forensics", "pattern-recognition"]

    def test_foreign_keys_enforced(self, test_db: sqlite3.Connection):
        """FK enforcement should be ON — inserting a bad FK should fail."""
        fk_status = test_db.execute("PRAGMA foreign_keys").fetchone()[0]
        assert fk_status == 1, "Foreign keys not enabled"

    def test_candidate_experience_check(self, tmp_path):
        """Negative experience should be rejected by CHECK constraint."""
        conn = get_connection(str(tmp_path / "check.db"))
        init_db(conn)
        try:
            conn.execute(
                "INSERT INTO candidates (name, experience_years, availability, quirk) "
                "VALUES ('Bad', -1, 'Immediate', NULL)"
            )
            assert False, "Should have raised IntegrityError"
        except sqlite3.IntegrityError:
            pass  # expected
        finally:
            conn.close()

    def test_availability_check(self, tmp_path):
        """Invalid availability value should be rejected by CHECK constraint."""
        conn = get_connection(str(tmp_path / "check2.db"))
        init_db(conn)
        try:
            conn.execute(
                "INSERT INTO candidates (name, experience_years, availability, quirk) "
                "VALUES ('Bad', 5, 'Maybe', NULL)"
            )
            assert False, "Should have raised IntegrityError"
        except sqlite3.IntegrityError:
            pass  # expected
        finally:
            conn.close()

    def test_macgyver_has_four_skills(self, test_db: sqlite3.Connection):
        """MacGyver should have 4 skills (most of any candidate)."""
        row = test_db.execute(
            "SELECT COUNT(*) AS cnt FROM candidate_skills cs "
            "JOIN candidates c ON cs.candidate_id = c.id "
            "WHERE c.name = 'MacGyver'"
        ).fetchone()
        assert row["cnt"] == 4


# ===================================================================
# Scoring unit tests
# ===================================================================

class TestComputeMatchScore:
    """Test the pure scoring function with controlled inputs."""

    def test_perfect_match(self):
        """All skills match, experience met, traits match, immediate."""
        result = compute_match_score(
            candidate_skills={"python", "sql", "fastapi"},
            job_required_skills={"python", "sql", "fastapi"},
            candidate_experience=5,
            job_min_experience=3,
            candidate_traits={"analytical", "curious"},
            job_culture_keywords={"analytical", "curious"},
            candidate_availability="Immediate",
        )
        assert result["score"] == 100.0
        assert result["skill_score"] == 60.0
        assert result["experience_score"] == 25.0
        assert result["trait_score"] == 10.0
        assert result["availability_score"] == 5.0
        assert result["meets_experience"] is True
        assert len(result["matched_skills"]) == 3

    def test_no_skills_overlap(self):
        """Zero skill overlap should give 0 skill score."""
        result = compute_match_score(
            candidate_skills={"cooking", "dancing"},
            job_required_skills={"python", "sql"},
            candidate_experience=10,
            job_min_experience=2,
            candidate_traits=set(),
            job_culture_keywords=set(),
            candidate_availability="Immediate",
        )
        assert result["skill_score"] == 0.0
        assert result["matched_skills"] == []
        assert result["experience_score"] == 25.0  # experience still counts

    def test_partial_skills(self):
        """Matching 2 of 3 skills should give (2/3)*60 = 40.0."""
        result = compute_match_score(
            candidate_skills={"python", "sql"},
            job_required_skills={"python", "sql", "docker"},
            candidate_experience=5,
            job_min_experience=5,
            candidate_traits=set(),
            job_culture_keywords=set(),
            candidate_availability="Immediate",
        )
        assert result["skill_score"] == 40.0
        assert sorted(result["matched_skills"]) == ["python", "sql"]

    def test_empty_candidate_skills(self):
        """Candidate with no skills should score 0 on skill match."""
        result = compute_match_score(
            candidate_skills=set(),
            job_required_skills={"python"},
            candidate_experience=1,
            job_min_experience=1,
            candidate_traits=set(),
            job_culture_keywords=set(),
            candidate_availability="Immediate",
        )
        assert result["skill_score"] == 0.0
        assert result["matched_skills"] == []

    def test_empty_job_skills(self):
        """Job with no required skills should give 0 skill score."""
        result = compute_match_score(
            candidate_skills={"python"},
            job_required_skills=set(),
            candidate_experience=5,
            job_min_experience=0,
            candidate_traits=set(),
            job_culture_keywords=set(),
            candidate_availability="Immediate",
        )
        assert result["skill_score"] == 0.0
        assert result["experience_score"] == 25.0

    def test_below_experience(self):
        """Below minimum experience should give proportional score."""
        result = compute_match_score(
            candidate_skills=set(),
            job_required_skills=set(),
            candidate_experience=2,
            job_min_experience=4,
            candidate_traits=set(),
            job_culture_keywords=set(),
            candidate_availability="Immediate",
        )
        assert result["experience_score"] == 12.5  # (2/4)*25
        assert result["meets_experience"] is False

    def test_zero_min_experience(self):
        """Zero minimum experience should give full 25 points."""
        result = compute_match_score(
            candidate_skills=set(),
            job_required_skills=set(),
            candidate_experience=0,
            job_min_experience=0,
            candidate_traits=set(),
            job_culture_keywords=set(),
            candidate_availability="Immediate",
        )
        assert result["experience_score"] == 25.0
        assert result["meets_experience"] is True

    def test_availability_immediate(self):
        result = compute_match_score(
            candidate_skills=set(), job_required_skills=set(),
            candidate_experience=0, job_min_experience=0,
            candidate_traits=set(), job_culture_keywords=set(),
            candidate_availability="Immediate",
        )
        assert result["availability_score"] == 5.0

    def test_availability_two_weeks(self):
        result = compute_match_score(
            candidate_skills=set(), job_required_skills=set(),
            candidate_experience=0, job_min_experience=0,
            candidate_traits=set(), job_culture_keywords=set(),
            candidate_availability="2 weeks",
        )
        assert result["availability_score"] == 3.0

    def test_availability_not_looking(self):
        result = compute_match_score(
            candidate_skills=set(), job_required_skills=set(),
            candidate_experience=0, job_min_experience=0,
            candidate_traits=set(), job_culture_keywords=set(),
            candidate_availability="Not looking",
        )
        assert result["availability_score"] == 0.0

    def test_trait_culture_match(self):
        """1 of 2 culture keywords matching should give (1/2)*10 = 5."""
        result = compute_match_score(
            candidate_skills=set(),
            job_required_skills=set(),
            candidate_experience=5,
            job_min_experience=0,
            candidate_traits={"analytical", "blunt"},
            job_culture_keywords={"analytical", "autonomous"},
            candidate_availability="Immediate",
        )
        assert result["trait_score"] == 5.0

    def test_case_insensitive_skills(self):
        """Skills should be compared case-insensitively."""
        result = compute_match_score(
            candidate_skills={"Python", "SQL"},
            job_required_skills={"python", "sql"},
            candidate_experience=5,
            job_min_experience=5,
            candidate_traits=set(),
            job_culture_keywords=set(),
            candidate_availability="Immediate",
        )
        assert result["skill_score"] == 60.0
        assert len(result["matched_skills"]) == 2

    def test_reason_string_is_nonempty(self):
        result = compute_match_score(
            candidate_skills={"a"},
            job_required_skills={"a", "b"},
            candidate_experience=3,
            job_min_experience=5,
            candidate_traits=set(),
            job_culture_keywords=set(),
            candidate_availability="2 weeks",
        )
        assert isinstance(result["reason"], str)
        assert len(result["reason"]) > 0


# ===================================================================
# Ranking / tie-breaking tests (against seeded data)
# ===================================================================

class TestRankingWithSeedData:
    """Test ranking functions against the full seeded database."""

    def test_backend_detective_top_candidate(self, test_db):
        """Sherlock H. should be the top match for Backend Detective (job 1)."""
        results = get_candidates_for_job(test_db, 1)
        assert results is not None
        assert results[0]["candidate_name"] == "Sherlock H."
        # Sherlock: 3/3 skills=60, exp 8>=3=25, trait 'analytical' matches 1/2 culture=5, Immediate=5 → 95.0
        assert results[0]["score"] == 95.0

    def test_rapid_proto_top_candidates(self, test_db):
        """Top matches for Rapid Prototyping Engineer should have systems-design + rapid-prototyping."""
        results = get_candidates_for_job(test_db, 2)
        assert results is not None
        # All of Rick S., Tony S., MacGyver have both skills
        top_names = [r["candidate_name"] for r in results[:3]]
        assert "Rick S." in top_names
        assert "Tony S." in top_names
        assert "MacGyver" in top_names

    def test_nonexistent_job_returns_none(self, test_db):
        result = get_candidates_for_job(test_db, 999)
        assert result is None

    def test_nonexistent_candidate_returns_none(self, test_db):
        result = get_jobs_for_candidate(test_db, 999)
        assert result is None

    def test_job_match_returns_all_candidates(self, test_db):
        """Every candidate should appear in the results for any job."""
        results = get_candidates_for_job(test_db, 1)
        assert len(results) == 15

    def test_candidate_match_returns_all_jobs(self, test_db):
        """Every job should appear in the results for any candidate."""
        results = get_jobs_for_candidate(test_db, 1)
        assert len(results) == 6

    def test_scores_are_descending(self, test_db):
        """Scores in results should be in non-increasing order."""
        results = get_candidates_for_job(test_db, 1)
        scores = [r["score"] for r in results]
        assert scores == sorted(scores, reverse=True)

    def test_candidate_scores_are_descending(self, test_db):
        """Scores in candidate→job results should be non-increasing."""
        results = get_jobs_for_candidate(test_db, 1)
        scores = [r["score"] for r in results]
        assert scores == sorted(scores, reverse=True)

    def test_deterministic_ordering(self, test_db):
        """Running the same query twice should produce identical order."""
        r1 = get_candidates_for_job(test_db, 4)
        r2 = get_candidates_for_job(test_db, 4)
        ids1 = [r["candidate_id"] for r in r1]
        ids2 = [r["candidate_id"] for r in r2]
        assert ids1 == ids2

    def test_sherlock_best_job_is_backend_detective(self, test_db):
        """Sherlock's top job match should be Backend Detective."""
        results = get_jobs_for_candidate(test_db, 1)  # Sherlock is candidate 1
        assert results[0]["job_title"] == "Backend Detective"
