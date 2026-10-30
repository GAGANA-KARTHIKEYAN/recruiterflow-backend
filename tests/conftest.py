"""
Shared pytest fixtures for all test modules.

Each fixture creates a fresh, temporary SQLite database so that tests
are fully isolated and repeatable.
"""

import sqlite3
from pathlib import Path

import pytest

from app.database import get_connection, init_db, seed_db


@pytest.fixture()
def test_db(tmp_path: Path) -> sqlite3.Connection:
    """
    Yield a seeded database connection for unit tests.

    The database lives in a pytest-managed temp directory and is
    automatically cleaned up after the test.
    """
    db_path = str(tmp_path / "test.db")
    conn = get_connection(db_path)
    init_db(conn)
    seed_db(conn)
    yield conn
    conn.close()


@pytest.fixture()
def client(tmp_path: Path, monkeypatch):
    """
    Yield a FastAPI TestClient backed by a temporary, seeded database.

    Monkeypatches ``app.database.DB_PATH`` so that every call to
    ``get_connection()`` (including inside route handlers) uses the
    test database instead of the real one.
    """
    db_path = tmp_path / "test_api.db"
    monkeypatch.setattr("app.database.DB_PATH", db_path)

    # Pre-create and seed the test database
    conn = get_connection(str(db_path))
    init_db(conn)
    seed_db(conn)
    conn.close()

    from fastapi.testclient import TestClient
    from app.main import app

    with TestClient(app) as tc:
        yield tc


@pytest.fixture()
def detective_db(tmp_path: Path) -> sqlite3.Connection:
    """
    Yield a database connection loaded with the SQL Detective schema
    and seed data (separate from the Recruiter Bot schema).
    """
    db_path = str(tmp_path / "detective.db")
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    # Read and execute the full SQL file (schema + seed + queries are
    # interleaved, but we only want schema + seed here).  We'll extract
    # just the DDL and DML statements.
    sql_file = Path(__file__).resolve().parent.parent / "sql" / "sql_detective.sql"
    full_sql = sql_file.read_text(encoding="utf-8")

    # Execute everything up to (but not including) the first QUESTION comment
    # Actually, it's simpler and more robust to execute the CREATE + INSERT
    # statements directly.
    conn.executescript("""
        CREATE TABLE recruiters (
            id   INT PRIMARY KEY,
            name VARCHAR(100),
            region VARCHAR(50)
        );

        CREATE TABLE job_postings (
            id            INT PRIMARY KEY,
            title         VARCHAR(100),
            recruiter_id  INT,
            department    VARCHAR(50),
            opened_date   DATE,
            status        VARCHAR(20)
        );

        CREATE TABLE applicants (
            id           INT PRIMARY KEY,
            full_name    VARCHAR(100),
            email        VARCHAR(100),
            source       VARCHAR(50),
            applied_date DATE
        );

        CREATE TABLE interviews (
            id              INT PRIMARY KEY,
            applicant_id    INT,
            job_posting_id  INT,
            stage           VARCHAR(20),
            scheduled_date  DATE,
            outcome         VARCHAR(20)
        );

        INSERT INTO recruiters VALUES
            (1, 'Priya Shah',       'APAC'),
            (2, 'Daniel Ortiz',     'NA'),
            (3, 'Fatima Al-Sayed',  'EMEA'),
            (4, 'Wei Zhang',        'APAC'),
            (5, 'Grace Okafor',     'EMEA');

        INSERT INTO job_postings VALUES
            (1, 'Backend Engineer I',   1, 'Engineering',     '2026-01-05', 'open'),
            (2, 'Backend Engineer I',   2, 'Engineering',     '2026-01-10', 'open'),
            (3, 'Data Analyst',         3, 'Data',            '2026-01-08', 'closed'),
            (4, 'Backend Engineer II',  1, 'Engineering',     '2026-02-01', 'open'),
            (5, 'DevOps Engineer',      4, 'Infrastructure',  '2026-01-20', 'open'),
            (6, 'Data Analyst',         5, 'Data',            '2026-02-05', 'on_hold'),
            (7, 'Backend Engineer I',   2, 'Engineering',     '2026-02-15', 'closed');

        INSERT INTO applicants VALUES
            (1,  'Ananya Rao',      'ananya.rao@mail.com',    'LinkedIn',  '2026-01-06'),
            (2,  'Ananya Rao',      'Ananya.Rao@mail.com',    'Referral',  '2026-02-04'),
            (3,  'Ben Turner',      'ben.turner@mail.com',    'Job Board', '2026-01-07'),
            (4,  'Chloe Martin',    'chloe.martin@mail.com',  NULL,        '2026-01-09'),
            (5,  'Devansh Patel',   'devansh.patel@mail.com', 'LinkedIn',  '2026-01-11'),
            (6,  'Elena Popescu',   'elena.popescu@mail.com', 'Referral',  '2026-01-12'),
            (7,  'Farid Haidari',   'farid.haidari@mail.com', 'Job Board', '2026-01-13'),
            (8,  'Grace Lin',       'grace.lin@mail.com',     'LinkedIn',  '2026-01-15'),
            (9,  'Hassan Malik',    'hassan.malik@mail.com',  NULL,        '2026-01-16'),
            (10, 'Isla Fraser',     'isla.fraser@mail.com',   'Referral',  '2026-01-18'),
            (11, 'Jonas Weber',     'jonas.weber@mail.com',   'Job Board', '2026-02-10');

        INSERT INTO interviews VALUES
            (1,  1,  1, 'Screen',    '2026-01-10', 'passed'),
            (2,  1,  1, 'Technical', '2026-01-15', 'passed'),
            (3,  1,  1, 'Final',     '2026-01-22', 'passed'),
            (4,  2,  4, 'Screen',    '2026-02-05', 'passed'),
            (5,  3,  1, 'Screen',    '2026-01-11', 'passed'),
            (6,  3,  1, 'Technical', '2026-01-16', 'failed'),
            (7,  3,  3, 'Final',     '2026-01-28', 'passed'),
            (8,  4,  1, 'Screen',    '2026-01-12', 'passed'),
            (9,  4,  1, 'Final',     '2026-01-24', 'failed'),
            (10, 5,  2, 'Screen',    '2026-01-14', 'passed'),
            (11, 5,  2, 'Technical', '2026-01-19', 'passed'),
            (12, 5,  2, 'Final',     '2026-01-25', 'passed'),
            (13, 6,  2, 'Screen',    '2026-01-15', 'passed'),
            (14, 6,  2, 'Final',     '2026-01-26', 'failed'),
            (15, 7,  2, 'Screen',    '2026-01-16', 'no_show'),
            (16, 8,  4, 'Screen',    '2026-02-03', 'passed'),
            (17, 8,  4, 'Technical', '2026-02-08', 'passed'),
            (18, 8,  4, 'Final',     '2026-02-12', 'passed'),
            (19, 9,  4, 'Screen',    '2026-02-04', 'passed'),
            (20, 9,  4, 'Final',     '2026-02-14', 'passed'),
            (21, 10, 5, 'Screen',    '2026-01-22', 'passed'),
            (22, 10, 5, 'Technical', '2026-01-28', NULL),
            (23, 11, 7, 'Final',     '2026-02-20', 'passed'),
            (24, 6,  7, 'Final',     '2026-02-21', 'failed');
    """)

    yield conn
    conn.close()
