"""
Pydantic models for API request/response validation.

These models define the JSON shape of every API response and enable
automatic validation, serialization, and OpenAPI documentation.
"""

from pydantic import BaseModel


# ---------------------------------------------------------------------------
# Match result models
# ---------------------------------------------------------------------------

class CandidateMatch(BaseModel):
    """One candidate's match result when ranking candidates for a job."""

    candidate_id: int
    candidate_name: str
    score: float
    matched_skills: list[str]
    experience_years: int
    meets_experience: bool
    availability: str
    skill_score: float
    experience_score: float
    trait_score: float
    availability_score: float
    reason: str


class JobMatch(BaseModel):
    """One job's match result when ranking jobs for a candidate."""

    job_id: int
    job_title: str
    score: float
    matched_skills: list[str]
    matched_skills_count: int
    min_experience: int
    meets_experience: bool
    skill_score: float
    experience_score: float
    trait_score: float
    availability_score: float
    reason: str


# ---------------------------------------------------------------------------
# Envelope response models
# ---------------------------------------------------------------------------

class JobMatchesResponse(BaseModel):
    """Response envelope for GET /jobs/{id}/matches."""

    job_id: int
    job_title: str
    matches: list[CandidateMatch]


class CandidateMatchesResponse(BaseModel):
    """Response envelope for GET /candidates/{id}/matches."""

    candidate_id: int
    candidate_name: str
    matches: list[JobMatch]


# ---------------------------------------------------------------------------
# Error model (for OpenAPI docs)
# ---------------------------------------------------------------------------

class ErrorResponse(BaseModel):
    """Standard error response body."""

    detail: str
