"""
Matching algorithm for ranking candidates against jobs and vice versa.

Score scale: 0–100 (rounded to 1 decimal place)
Components and weights:
    Skill match ........  60 pts  — matched / required skills
    Experience fit .....  25 pts  — full if >= minimum, proportional if below
    Trait / culture ....  10 pts  — candidate traits matching job culture keywords
    Availability .......   5 pts  — Immediate=5, 2 weeks=3, Not looking=0

All string comparisons (skills, traits, culture keywords) are normalized
by stripping whitespace and lowercasing.  Each required skill is counted at
most once.  There is no semantic or AI-based matching — only exact
normalized string equality.

Why a perfect skill + experience fit may still score below 100:
    The maximum from skills (60) + experience (25) = 85.  The remaining 15
    points come from trait/culture match (10) and availability (5).  A
    candidate whose traits do not overlap with a job's culture keywords,
    or who is "Not looking", will not earn those bonus points.
"""

import sqlite3


def _normalize(value: str) -> str:
    """Normalize for comparison: strip whitespace, lowercase."""
    return value.strip().lower()


# Availability → bonus points
_AVAILABILITY_BONUS: dict[str, float] = {
    "Immediate": 5.0,
    "2 weeks": 3.0,
    "Not looking": 0.0,
}


# ---------------------------------------------------------------------------
# Core scoring function
# ---------------------------------------------------------------------------

def compute_match_score(
    candidate_skills: set[str],
    job_required_skills: set[str],
    candidate_experience: int,
    job_min_experience: int,
    candidate_traits: set[str],
    job_culture_keywords: set[str],
    candidate_availability: str,
) -> dict:
    """
    Compute a match score between a candidate and a job.

    Parameters
    ----------
    candidate_skills : set of skill name strings (already normalized)
    job_required_skills : set of skill name strings (already normalized)
    candidate_experience : years of experience
    job_min_experience : minimum years required by the job
    candidate_traits : set of trait strings (already normalized)
    job_culture_keywords : set of culture keyword strings (already normalized)
    candidate_availability : one of 'Immediate', '2 weeks', 'Not looking'

    Returns
    -------
    dict with keys: score, matched_skills, skill_score, experience_score,
                    trait_score, availability_score, meets_experience, reason
    """
    # --- 1. Skill match (60 pts max) ---
    if len(job_required_skills) == 0:
        # No required skills → no skill score to earn
        skill_score = 0.0
        matched_skills: list[str] = []
    else:
        norm_candidate = {_normalize(s) for s in candidate_skills}
        norm_required = {_normalize(s) for s in job_required_skills}
        matched = norm_candidate & norm_required          # each counted at most once
        matched_skills = sorted(matched)                  # sorted for determinism
        skill_score = (len(matched) / len(norm_required)) * 60.0

    # --- 2. Experience fit (25 pts max) ---
    if job_min_experience == 0:
        # Zero minimum → everyone qualifies, no division by zero
        experience_score = 25.0
        meets_experience = True
    elif candidate_experience >= job_min_experience:
        experience_score = 25.0
        meets_experience = True
    else:
        experience_score = (candidate_experience / job_min_experience) * 25.0
        meets_experience = False

    # --- 3. Trait / culture keyword match (10 pts max) ---
    if len(job_culture_keywords) == 0:
        trait_score = 0.0
        matched_keywords: list[str] = []
    else:
        norm_traits = {_normalize(t) for t in candidate_traits}
        norm_keywords = {_normalize(k) for k in job_culture_keywords}
        kw_matched = norm_traits & norm_keywords
        matched_keywords = sorted(kw_matched)
        trait_score = (len(kw_matched) / len(norm_keywords)) * 10.0

    # --- 4. Availability bonus (5 pts max) ---
    availability_score = _AVAILABILITY_BONUS.get(candidate_availability, 0.0)

    # --- Total (capped at 100, rounded to 1 decimal) ---
    total = min(
        skill_score + experience_score + trait_score + availability_score,
        100.0,
    )
    total = round(total, 1)

    # --- Human-readable reason ---
    parts: list[str] = []

    if len(job_required_skills) > 0:
        skill_list = f" ({', '.join(matched_skills)})" if matched_skills else ""
        parts.append(
            f"Matched {len(matched_skills)}/{len(job_required_skills)} "
            f"required skills{skill_list}."
        )
    else:
        parts.append("Job has no required skills.")

    if meets_experience:
        if job_min_experience == 0:
            parts.append("No minimum experience required.")
        else:
            parts.append(
                f"Meets experience requirement "
                f"({candidate_experience} >= {job_min_experience} yrs)."
            )
    else:
        parts.append(
            f"Below minimum experience "
            f"({candidate_experience} < {job_min_experience} yrs)."
        )

    if candidate_availability == "Immediate":
        parts.append("Available immediately.")
    elif candidate_availability == "2 weeks":
        parts.append("Available in 2 weeks.")
    else:
        parts.append("Not currently looking.")

    return {
        "score": total,
        "matched_skills": matched_skills,
        "skill_score": round(skill_score, 1),
        "experience_score": round(experience_score, 1),
        "trait_score": round(trait_score, 1),
        "availability_score": round(availability_score, 1),
        "meets_experience": meets_experience,
        "reason": " ".join(parts),
    }


# ---------------------------------------------------------------------------
# Database-aware helpers (raw SQL, no ORM)
# ---------------------------------------------------------------------------

def _candidate_skills(conn: sqlite3.Connection, cid: int) -> set[str]:
    """Return the set of normalized skill names for a candidate."""
    rows = conn.execute(
        "SELECT s.name FROM candidate_skills cs "
        "JOIN skills s ON cs.skill_id = s.id "
        "WHERE cs.candidate_id = ?",
        (cid,),
    ).fetchall()
    return {row["name"] for row in rows}


def _candidate_traits(conn: sqlite3.Connection, cid: int) -> set[str]:
    """Return the set of normalized trait strings for a candidate."""
    rows = conn.execute(
        "SELECT trait FROM candidate_traits WHERE candidate_id = ?", (cid,)
    ).fetchall()
    return {row["trait"] for row in rows}


def _job_skills(conn: sqlite3.Connection, jid: int) -> set[str]:
    """Return the set of normalized required skill names for a job."""
    rows = conn.execute(
        "SELECT s.name FROM job_skills js "
        "JOIN skills s ON js.skill_id = s.id "
        "WHERE js.job_id = ?",
        (jid,),
    ).fetchall()
    return {row["name"] for row in rows}


def _job_culture_keywords(conn: sqlite3.Connection, jid: int) -> set[str]:
    """Return the set of normalized culture keywords for a job."""
    rows = conn.execute(
        "SELECT keyword FROM job_culture_keywords WHERE job_id = ?", (jid,)
    ).fetchall()
    return {row["keyword"] for row in rows}


# ---------------------------------------------------------------------------
# Public API — used by route handlers
# ---------------------------------------------------------------------------

def get_candidates_for_job(
    conn: sqlite3.Connection, job_id: int
) -> list[dict] | None:
    """
    Rank all candidates for *job_id*.

    Returns ``None`` when the job does not exist.
    Tie-breaking order:
        1. score  DESC
        2. candidate experience  DESC
        3. candidate name  ASC
        4. candidate id  ASC
    """
    job = conn.execute(
        "SELECT id, title, min_experience FROM jobs WHERE id = ?", (job_id,)
    ).fetchone()
    if job is None:
        return None

    required = _job_skills(conn, job_id)
    culture = _job_culture_keywords(conn, job_id)

    candidates = conn.execute(
        "SELECT id, name, experience_years, availability, quirk "
        "FROM candidates"
    ).fetchall()

    results: list[dict] = []
    for c in candidates:
        match = compute_match_score(
            candidate_skills=_candidate_skills(conn, c["id"]),
            job_required_skills=required,
            candidate_experience=c["experience_years"],
            job_min_experience=job["min_experience"],
            candidate_traits=_candidate_traits(conn, c["id"]),
            job_culture_keywords=culture,
            candidate_availability=c["availability"],
        )
        results.append(
            {
                "candidate_id": c["id"],
                "candidate_name": c["name"],
                "score": match["score"],
                "matched_skills": match["matched_skills"],
                "experience_years": c["experience_years"],
                "meets_experience": match["meets_experience"],
                "availability": c["availability"],
                "skill_score": match["skill_score"],
                "experience_score": match["experience_score"],
                "trait_score": match["trait_score"],
                "availability_score": match["availability_score"],
                "reason": match["reason"],
            }
        )

    # Deterministic sort
    results.sort(
        key=lambda r: (
            -r["score"],
            -r["experience_years"],
            r["candidate_name"],
            r["candidate_id"],
        )
    )
    return results


def get_jobs_for_candidate(
    conn: sqlite3.Connection, candidate_id: int
) -> list[dict] | None:
    """
    Rank all jobs for *candidate_id*.

    Returns ``None`` when the candidate does not exist.
    Tie-breaking order:
        1. score  DESC
        2. matched skills count  DESC
        3. job title  ASC
        4. job id  ASC
    """
    candidate = conn.execute(
        "SELECT id, name, experience_years, availability "
        "FROM candidates WHERE id = ?",
        (candidate_id,),
    ).fetchone()
    if candidate is None:
        return None

    c_skills = _candidate_skills(conn, candidate_id)
    c_traits = _candidate_traits(conn, candidate_id)

    jobs = conn.execute(
        "SELECT id, title, min_experience, tagline FROM jobs"
    ).fetchall()

    results: list[dict] = []
    for j in jobs:
        match = compute_match_score(
            candidate_skills=c_skills,
            job_required_skills=_job_skills(conn, j["id"]),
            candidate_experience=candidate["experience_years"],
            job_min_experience=j["min_experience"],
            candidate_traits=c_traits,
            job_culture_keywords=_job_culture_keywords(conn, j["id"]),
            candidate_availability=candidate["availability"],
        )
        results.append(
            {
                "job_id": j["id"],
                "job_title": j["title"],
                "score": match["score"],
                "matched_skills": match["matched_skills"],
                "matched_skills_count": len(match["matched_skills"]),
                "min_experience": j["min_experience"],
                "meets_experience": match["meets_experience"],
                "skill_score": match["skill_score"],
                "experience_score": match["experience_score"],
                "trait_score": match["trait_score"],
                "availability_score": match["availability_score"],
                "reason": match["reason"],
            }
        )

    # Deterministic sort
    results.sort(
        key=lambda r: (
            -r["score"],
            -r["matched_skills_count"],
            r["job_title"],
            r["job_id"],
        )
    )
    return results
