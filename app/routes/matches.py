"""
API route handlers for the matching endpoints.

Both endpoints use raw SQL via app.database and the scoring logic
from app.matching.  No ORM or query builder is involved.
"""

from fastapi import APIRouter, HTTPException

from app.database import get_connection
from app.matching import get_candidates_for_job, get_jobs_for_candidate
from app.models import (
    CandidateMatch,
    CandidateMatchesResponse,
    ErrorResponse,
    JobMatch,
    JobMatchesResponse,
)

router = APIRouter()


@router.get(
    "/jobs/{job_id}/matches",
    response_model=JobMatchesResponse,
    summary="Get ranked candidates for a job",
    description=(
        "Return every candidate ranked by match score for the specified job.  "
        "Sorting: score DESC → experience DESC → name ASC → id ASC."
    ),
    responses={404: {"model": ErrorResponse, "description": "Job not found"}},
)
def job_matches(job_id: int):
    conn = get_connection()
    try:
        # Verify the job exists (raw SQL)
        job = conn.execute(
            "SELECT id, title FROM jobs WHERE id = ?", (job_id,)
        ).fetchone()
        if job is None:
            raise HTTPException(
                status_code=404,
                detail=f"Job with id {job_id} not found",
            )

        results = get_candidates_for_job(conn, job_id)

        return JobMatchesResponse(
            job_id=job["id"],
            job_title=job["title"],
            matches=[CandidateMatch(**r) for r in results],
        )
    finally:
        conn.close()


@router.get(
    "/candidates/{candidate_id}/matches",
    response_model=CandidateMatchesResponse,
    summary="Get ranked jobs for a candidate",
    description=(
        "Return every job ranked by match score for the specified candidate.  "
        "Sorting: score DESC → matched-skills count DESC → title ASC → id ASC."
    ),
    responses={
        404: {"model": ErrorResponse, "description": "Candidate not found"}
    },
)
def candidate_matches(candidate_id: int):
    conn = get_connection()
    try:
        candidate = conn.execute(
            "SELECT id, name FROM candidates WHERE id = ?",
            (candidate_id,),
        ).fetchone()
        if candidate is None:
            raise HTTPException(
                status_code=404,
                detail=f"Candidate with id {candidate_id} not found",
            )

        results = get_jobs_for_candidate(conn, candidate_id)

        return CandidateMatchesResponse(
            candidate_id=candidate["id"],
            candidate_name=candidate["name"],
            matches=[JobMatch(**r) for r in results],
        )
    finally:
        conn.close()
