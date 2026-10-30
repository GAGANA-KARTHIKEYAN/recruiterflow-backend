"""
Tests for the API endpoints using FastAPI TestClient.

Covers:
    - Both matching endpoints with valid IDs
    - 404 responses for nonexistent IDs
    - Response structure validation
    - Health check endpoint
"""


class TestHealthCheck:
    def test_root_returns_ok(self, client):
        resp = client.get("/")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"


class TestJobMatchesEndpoint:
    """Tests for GET /jobs/{id}/matches."""

    def test_valid_job(self, client):
        """Should return 200 with a list of candidate matches."""
        resp = client.get("/jobs/1/matches")
        assert resp.status_code == 200
        data = resp.json()
        assert data["job_id"] == 1
        assert data["job_title"] == "Backend Detective"
        assert isinstance(data["matches"], list)
        assert len(data["matches"]) == 15  # all candidates

    def test_match_structure(self, client):
        """Each match should have the required fields."""
        resp = client.get("/jobs/1/matches")
        match = resp.json()["matches"][0]
        required_fields = [
            "candidate_id", "candidate_name", "score",
            "matched_skills", "experience_years", "meets_experience",
            "availability", "skill_score", "experience_score",
            "trait_score", "availability_score", "reason",
        ]
        for field in required_fields:
            assert field in match, f"Missing field: {field}"

    def test_scores_are_sorted(self, client):
        """Matches should be sorted by score descending."""
        resp = client.get("/jobs/1/matches")
        matches = resp.json()["matches"]
        scores = [m["score"] for m in matches]
        assert scores == sorted(scores, reverse=True)

    def test_nonexistent_job_returns_404(self, client):
        resp = client.get("/jobs/999/matches")
        assert resp.status_code == 404
        assert "not found" in resp.json()["detail"].lower()

    def test_negative_job_id(self, client):
        resp = client.get("/jobs/-1/matches")
        assert resp.status_code == 404

    def test_all_six_jobs_work(self, client):
        """All 6 seeded jobs should return 200."""
        for job_id in range(1, 7):
            resp = client.get(f"/jobs/{job_id}/matches")
            assert resp.status_code == 200, f"Job {job_id} failed"


class TestCandidateMatchesEndpoint:
    """Tests for GET /candidates/{id}/matches."""

    def test_valid_candidate(self, client):
        """Should return 200 with a list of job matches."""
        resp = client.get("/candidates/1/matches")
        assert resp.status_code == 200
        data = resp.json()
        assert data["candidate_id"] == 1
        assert data["candidate_name"] == "Sherlock H."
        assert isinstance(data["matches"], list)
        assert len(data["matches"]) == 6  # all jobs

    def test_match_structure(self, client):
        """Each match should have the required fields."""
        resp = client.get("/candidates/1/matches")
        match = resp.json()["matches"][0]
        required_fields = [
            "job_id", "job_title", "score",
            "matched_skills", "matched_skills_count",
            "min_experience", "meets_experience",
            "skill_score", "experience_score",
            "trait_score", "availability_score", "reason",
        ]
        for field in required_fields:
            assert field in match, f"Missing field: {field}"

    def test_scores_are_sorted(self, client):
        """Matches should be sorted by score descending."""
        resp = client.get("/candidates/1/matches")
        matches = resp.json()["matches"]
        scores = [m["score"] for m in matches]
        assert scores == sorted(scores, reverse=True)

    def test_nonexistent_candidate_returns_404(self, client):
        resp = client.get("/candidates/999/matches")
        assert resp.status_code == 404
        assert "not found" in resp.json()["detail"].lower()

    def test_all_fifteen_candidates_work(self, client):
        """All 15 seeded candidates should return 200."""
        for cid in range(1, 16):
            resp = client.get(f"/candidates/{cid}/matches")
            assert resp.status_code == 200, f"Candidate {cid} failed"


class TestSpecificMatches:
    """Verify specific expected match outcomes."""

    def test_sherlock_top_for_backend_detective(self, client):
        """Sherlock should be the #1 match for Backend Detective."""
        resp = client.get("/jobs/1/matches")
        top = resp.json()["matches"][0]
        assert top["candidate_name"] == "Sherlock H."
        assert top["score"] == 95.0

    def test_sherlock_matches_all_detective_skills(self, client):
        resp = client.get("/jobs/1/matches")
        top = resp.json()["matches"][0]
        assert sorted(top["matched_skills"]) == [
            "deduction", "forensics", "pattern-recognition"
        ]

    def test_not_looking_candidates_still_returned(self, client):
        """Candidates with 'Not looking' availability should still appear."""
        resp = client.get("/jobs/1/matches")
        names = [m["candidate_name"] for m in resp.json()["matches"]]
        # Tony S. is "Not looking"
        assert "Tony S." in names

    def test_backend_detective_top_match_for_sherlock(self, client):
        """Sherlock's best job should be Backend Detective."""
        resp = client.get("/candidates/1/matches")
        top = resp.json()["matches"][0]
        assert top["job_title"] == "Backend Detective"
