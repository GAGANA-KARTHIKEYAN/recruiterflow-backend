"""
Database initialization, connection management, and seed data.

Uses raw SQL with Python's built-in sqlite3 module.
No ORM or query builder — every statement is hand-written.
"""

import sqlite3
from pathlib import Path


# ---------------------------------------------------------------------------
# Database file location
# ---------------------------------------------------------------------------
DB_DIR = Path(__file__).resolve().parent.parent / "data"
DB_PATH = DB_DIR / "recruiterflow.db"


# ---------------------------------------------------------------------------
# Connection helper
# ---------------------------------------------------------------------------
def get_connection(db_path: str | None = None) -> sqlite3.Connection:
    """
    Create and return a SQLite connection.

    - Enables foreign-key enforcement (required on every connection in SQLite).
    - Sets row_factory to sqlite3.Row for dict-like column access.
    """
    path = db_path or str(DB_PATH)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


# ---------------------------------------------------------------------------
# Schema creation
# ---------------------------------------------------------------------------
def init_db(conn: sqlite3.Connection) -> None:
    """Create all tables, constraints, and indexes using raw SQL."""
    conn.executescript("""
        -- =================================================================
        -- Candidates
        -- =================================================================
        CREATE TABLE IF NOT EXISTS candidates (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            name             TEXT    NOT NULL,
            experience_years INTEGER NOT NULL CHECK (experience_years >= 0),
            availability     TEXT    NOT NULL CHECK (
                                 availability IN ('Immediate', '2 weeks', 'Not looking')
                             ),
            quirk            TEXT
        );

        -- =================================================================
        -- Skills (normalized lookup shared by candidates and jobs)
        -- =================================================================
        CREATE TABLE IF NOT EXISTS skills (
            id   INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT    NOT NULL UNIQUE          -- stored lowercase, trimmed
        );

        -- =================================================================
        -- Candidate ↔ Skill (many-to-many)
        -- =================================================================
        CREATE TABLE IF NOT EXISTS candidate_skills (
            candidate_id INTEGER NOT NULL,
            skill_id     INTEGER NOT NULL,
            PRIMARY KEY (candidate_id, skill_id),
            FOREIGN KEY (candidate_id) REFERENCES candidates (id) ON DELETE CASCADE,
            FOREIGN KEY (skill_id)     REFERENCES skills     (id) ON DELETE CASCADE
        );

        -- =================================================================
        -- Candidate traits (many-to-many, trait stored as normalized text)
        -- =================================================================
        CREATE TABLE IF NOT EXISTS candidate_traits (
            candidate_id INTEGER NOT NULL,
            trait         TEXT    NOT NULL,        -- stored lowercase, trimmed
            PRIMARY KEY (candidate_id, trait),
            FOREIGN KEY (candidate_id) REFERENCES candidates (id) ON DELETE CASCADE
        );

        -- =================================================================
        -- Jobs
        -- =================================================================
        CREATE TABLE IF NOT EXISTS jobs (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            title          TEXT    NOT NULL,
            min_experience INTEGER NOT NULL CHECK (min_experience >= 0),
            tagline        TEXT
        );

        -- =================================================================
        -- Job ↔ Skill (many-to-many)
        -- =================================================================
        CREATE TABLE IF NOT EXISTS job_skills (
            job_id   INTEGER NOT NULL,
            skill_id INTEGER NOT NULL,
            PRIMARY KEY (job_id, skill_id),
            FOREIGN KEY (job_id)   REFERENCES jobs   (id) ON DELETE CASCADE,
            FOREIGN KEY (skill_id) REFERENCES skills (id) ON DELETE CASCADE
        );

        -- =================================================================
        -- Job culture keywords (many-to-many, keyword as normalized text)
        -- =================================================================
        CREATE TABLE IF NOT EXISTS job_culture_keywords (
            job_id  INTEGER NOT NULL,
            keyword TEXT    NOT NULL,              -- stored lowercase, trimmed
            PRIMARY KEY (job_id, keyword),
            FOREIGN KEY (job_id) REFERENCES jobs (id) ON DELETE CASCADE
        );

        -- =================================================================
        -- Indexes for frequently used joins
        -- =================================================================
        CREATE INDEX IF NOT EXISTS idx_cs_candidate
            ON candidate_skills (candidate_id);
        CREATE INDEX IF NOT EXISTS idx_cs_skill
            ON candidate_skills (skill_id);
        CREATE INDEX IF NOT EXISTS idx_js_job
            ON job_skills (job_id);
        CREATE INDEX IF NOT EXISTS idx_js_skill
            ON job_skills (skill_id);
        CREATE INDEX IF NOT EXISTS idx_ct_candidate
            ON candidate_traits (candidate_id);
        CREATE INDEX IF NOT EXISTS idx_jck_job
            ON job_culture_keywords (job_id);
    """)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------
def _normalize(value: str) -> str:
    """Normalize a string for storage/comparison: strip whitespace, lowercase."""
    return value.strip().lower()


def _get_or_create_skill(conn: sqlite3.Connection, skill_name: str) -> int:
    """Return the skill id for *skill_name*, inserting it first if needed."""
    normalized = _normalize(skill_name)
    row = conn.execute(
        "SELECT id FROM skills WHERE name = ?", (normalized,)
    ).fetchone()
    if row:
        return row["id"]
    cursor = conn.execute("INSERT INTO skills (name) VALUES (?)", (normalized,))
    return cursor.lastrowid


# ---------------------------------------------------------------------------
# Seed data — faithfully transcribed from the assignment PDF
# ---------------------------------------------------------------------------
CANDIDATES = [
    {
        "name": "Sherlock H.",
        "skills": ["deduction", "pattern-recognition", "forensics"],
        "experience_years": 8,
        "availability": "Immediate",
        "traits": ["analytical", "blunt"],
        "quirk": (
            "Solves problems by eliminating the impossible; "
            "occasionally insufferable in standups."
        ),
    },
    {
        "name": "Hermione G.",
        "skills": ["research", "time-management", "public-speaking"],
        "experience_years": 4,
        "availability": "2 weeks",
        "traits": ["detail-oriented", "overachiever"],
        "quirk": (
            "Reads the entire documentation before writing a single line of code."
        ),
    },
    {
        "name": "Tony S.",
        "skills": ["systems-design", "rapid-prototyping", "leadership"],
        "experience_years": 12,
        "availability": "Not looking",
        "traits": ["confident", "innovative"],
        "quirk": "Ships an MVP overnight, refuses to write tests.",
    },
    {
        "name": "Leslie K.",
        "skills": ["project-management", "stakeholder-management", "public-speaking"],
        "experience_years": 6,
        "availability": "Immediate",
        "traits": ["tenacious", "organized"],
        "quirk": "Has a binder for everything, including the binder.",
    },
    {
        "name": "Ron S.",
        "skills": ["woodworking", "minimalism", "negotiation"],
        "experience_years": 15,
        "availability": "Not looking",
        "traits": ["stubborn", "principled"],
        "quirk": "Refuses to use more than one monitor.",
    },
    {
        "name": "Rick S.",
        "skills": ["systems-design", "rapid-prototyping", "chemistry"],
        "experience_years": 20,
        "availability": "Immediate",
        "traits": ["genius", "reckless"],
        "quirk": "Solution works, mechanism deeply concerning.",
    },
    {
        "name": "Elle W.",
        "skills": ["persuasion", "research", "public-speaking"],
        "experience_years": 3,
        "availability": "Immediate",
        "traits": ["optimistic", "sharp"],
        "quirk": "Underestimated in every standup, correct in every retro.",
    },
    {
        "name": "MacGyver",
        "skills": [
            "rapid-prototyping",
            "resourcefulness",
            "chemistry",
            "systems-design",
        ],
        "experience_years": 10,
        "availability": "2 weeks",
        "traits": ["calm", "improviser"],
        "quirk": (
            "Fixes production outages with duct tape and a paperclip metaphor."
        ),
    },
    {
        "name": "Sheldon C.",
        "skills": ["theoretical-analysis", "pattern-recognition", "research"],
        "experience_years": 9,
        "availability": "Immediate",
        "traits": ["rigid", "brilliant"],
        "quirk": "Correct 95% of the time, insufferable 100% of the time.",
    },
    {
        "name": "Katniss E.",
        "skills": ["precision", "strategy", "crisis-management"],
        "experience_years": 5,
        "availability": "Immediate",
        "traits": ["resilient", "decisive"],
        "quirk": "Excellent under pressure, terrible with public speaking.",
    },
    {
        "name": "Michael S.",
        "skills": ["sales", "public-speaking", "team-building"],
        "experience_years": 11,
        "availability": "Not looking",
        "traits": ["enthusiastic", "chaotic"],
        "quirk": "World's best boss, according to a mug he bought himself.",
    },
    {
        "name": "Olivia P.",
        "skills": [
            "crisis-management",
            "negotiation",
            "strategy",
            "leadership",
        ],
        "experience_years": 13,
        "availability": "2 weeks",
        "traits": ["decisive", "intense"],
        "quirk": "Handles it. Whatever it is.",
    },
    {
        "name": "Ted L.",
        "skills": [
            "team-building",
            "optimism",
            "mentorship",
            "public-speaking",
        ],
        "experience_years": 7,
        "availability": "Immediate",
        "traits": ["empathetic", "persistent"],
        "quirk": "Turns every technical setback into a folksy metaphor.",
    },
    {
        "name": "Miranda P.",
        "skills": [
            "leadership",
            "negotiation",
            "stakeholder-management",
            "precision",
        ],
        "experience_years": 18,
        "availability": "Not looking",
        "traits": ["demanding", "decisive"],
        "quirk": (
            "Reviews every PR personally. Says nothing. Everyone panics."
        ),
    },
    {
        "name": "Dwight S.",
        "skills": ["sales", "negotiation", "security", "loyalty"],
        "experience_years": 9,
        "availability": "Immediate",
        "traits": ["intense", "loyal"],
        "quirk": "Assistant to the regional backend engineer.",
    },
]

JOBS = [
    {
        "title": "Backend Detective",
        "skills": ["deduction", "pattern-recognition", "forensics"],
        "min_experience": 3,
        "culture_keywords": ["analytical", "autonomous"],
        "tagline": "We have a bug. We have no leads. We have you.",
    },
    {
        "title": "Rapid Prototyping Engineer",
        "skills": ["rapid-prototyping", "systems-design"],
        "min_experience": 2,
        "culture_keywords": ["innovative", "fast-paced"],
        "tagline": (
            "Ship first, document never (kidding \u2014 please document)."
        ),
    },
    {
        "title": "Developer Relations Lead",
        "skills": ["public-speaking", "research"],
        "min_experience": 2,
        "culture_keywords": ["energetic", "curious"],
        "tagline": "Explain complex things to confused humans, cheerfully.",
    },
    {
        "title": "Engineering Manager, Chaos Team",
        "skills": ["team-building", "stakeholder-management", "leadership"],
        "min_experience": 5,
        "culture_keywords": ["empathetic", "organized"],
        "tagline": "Herd cats. The cats are senior engineers.",
    },
    {
        "title": "Incident Commander",
        "skills": ["crisis-management", "strategy", "negotiation"],
        "min_experience": 4,
        "culture_keywords": ["decisive", "calm-under-pressure"],
        "tagline": "3am page. You\u2019re the one who picks up.",
    },
    {
        "title": "Sales Engineer",
        "skills": ["sales", "public-speaking", "negotiation"],
        "min_experience": 3,
        "culture_keywords": ["enthusiastic", "persistent"],
        "tagline": "Sell the vision, then go build it.",
    },
]


def seed_db(conn: sqlite3.Connection) -> None:
    """Insert all candidate and job seed data from the assignment PDF."""

    for c in CANDIDATES:
        cursor = conn.execute(
            "INSERT INTO candidates (name, experience_years, availability, quirk) "
            "VALUES (?, ?, ?, ?)",
            (c["name"], c["experience_years"], c["availability"], c["quirk"]),
        )
        cid = cursor.lastrowid

        for skill in c["skills"]:
            sid = _get_or_create_skill(conn, skill)
            conn.execute(
                "INSERT INTO candidate_skills (candidate_id, skill_id) VALUES (?, ?)",
                (cid, sid),
            )

        for trait in c["traits"]:
            conn.execute(
                "INSERT INTO candidate_traits (candidate_id, trait) VALUES (?, ?)",
                (cid, _normalize(trait)),
            )

    for j in JOBS:
        cursor = conn.execute(
            "INSERT INTO jobs (title, min_experience, tagline) VALUES (?, ?, ?)",
            (j["title"], j["min_experience"], j["tagline"]),
        )
        jid = cursor.lastrowid

        for skill in j["skills"]:
            sid = _get_or_create_skill(conn, skill)
            conn.execute(
                "INSERT INTO job_skills (job_id, skill_id) VALUES (?, ?)",
                (jid, sid),
            )

        for keyword in j["culture_keywords"]:
            conn.execute(
                "INSERT INTO job_culture_keywords (job_id, keyword) VALUES (?, ?)",
                (jid, _normalize(keyword)),
            )

    conn.commit()
