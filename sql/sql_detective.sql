-- =============================================================================
-- SQL Detective Challenge — RecruiterFlow Backend Assignment
-- =============================================================================
-- This file runs against the hiring-ops schema provided in the assignment PDF.
-- Schema: recruiters, job_postings, applicants, interviews
-- Each query is preceded by a comment identifying the question number.
-- =============================================================================


-- ---------------------------------------------------------------------------
-- SCHEMA (from the assignment PDF — included here so the file is self-contained)
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS recruiters (
    id   INT PRIMARY KEY,
    name VARCHAR(100),
    region VARCHAR(50)
);

CREATE TABLE IF NOT EXISTS job_postings (
    id            INT PRIMARY KEY,
    title         VARCHAR(100),
    recruiter_id  INT,
    department    VARCHAR(50),
    opened_date   DATE,
    status        VARCHAR(20)   -- 'open', 'closed', 'on_hold'
);

CREATE TABLE IF NOT EXISTS applicants (
    id           INT PRIMARY KEY,
    full_name    VARCHAR(100),
    email        VARCHAR(100),
    source       VARCHAR(50),   -- nullable
    applied_date DATE
);

CREATE TABLE IF NOT EXISTS interviews (
    id              INT PRIMARY KEY,
    applicant_id    INT,
    job_posting_id  INT,
    stage           VARCHAR(20),   -- 'Screen', 'Technical', 'Final'
    scheduled_date  DATE,
    outcome         VARCHAR(20)    -- 'passed', 'failed', 'no_show', NULL (pending)
);


-- ---------------------------------------------------------------------------
-- SEED DATA (from the assignment PDF)
-- ---------------------------------------------------------------------------

INSERT OR IGNORE INTO recruiters VALUES
    (1, 'Priya Shah',       'APAC'),
    (2, 'Daniel Ortiz',     'NA'),
    (3, 'Fatima Al-Sayed',  'EMEA'),
    (4, 'Wei Zhang',        'APAC'),
    (5, 'Grace Okafor',     'EMEA');

INSERT OR IGNORE INTO job_postings VALUES
    (1, 'Backend Engineer I',   1, 'Engineering',     '2026-01-05', 'open'),
    (2, 'Backend Engineer I',   2, 'Engineering',     '2026-01-10', 'open'),
    (3, 'Data Analyst',         3, 'Data',            '2026-01-08', 'closed'),
    (4, 'Backend Engineer II',  1, 'Engineering',     '2026-02-01', 'open'),
    (5, 'DevOps Engineer',      4, 'Infrastructure',  '2026-01-20', 'open'),
    (6, 'Data Analyst',         5, 'Data',            '2026-02-05', 'on_hold'),
    (7, 'Backend Engineer I',   2, 'Engineering',     '2026-02-15', 'closed');

INSERT OR IGNORE INTO applicants VALUES
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

INSERT OR IGNORE INTO interviews VALUES
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


-- ===========================================================================
-- QUESTION 1
-- List all currently open job postings, along with the name of the recruiter
-- who owns each one.
-- ===========================================================================

SELECT jp.id            AS job_id,
       jp.title         AS job_title,
       jp.department,
       jp.opened_date,
       r.name           AS recruiter_name
  FROM job_postings jp
  JOIN recruiters r ON jp.recruiter_id = r.id
 WHERE jp.status = 'open'
 ORDER BY jp.id;


-- ===========================================================================
-- QUESTION 2
-- For each job posting, how many applicants reached the Final interview
-- stage?  Jobs with zero Final-stage applicants must still appear.
-- ===========================================================================

SELECT jp.id                              AS job_id,
       jp.title                           AS job_title,
       COUNT(DISTINCT i.applicant_id)     AS final_stage_applicants
  FROM job_postings jp
  LEFT JOIN interviews i
         ON jp.id = i.job_posting_id
        AND i.stage = 'Final'
 GROUP BY jp.id, jp.title
 ORDER BY jp.id;


-- ===========================================================================
-- QUESTION 3
-- Find every person who effectively applied to more than one job posting.
--
-- Approach:
--   - The data contains duplicate applicant records for the same person
--     (e.g. Ananya Rao with ids 1 and 2, emails differing only in case).
--   - normalize emails with LOWER() to group these duplicates.
--   - use interview records to associate applicants with job postings
--     (an applicant is linked to a job posting through their interviews).
--   - then count distinct job postings per normalized email and keep
--     only those with more than one.
-- ===========================================================================

SELECT LOWER(a.email)                     AS normalized_email,
       MAX(a.full_name)                   AS full_name,
       COUNT(DISTINCT i.job_posting_id)   AS jobs_applied_to
  FROM applicants a
  JOIN interviews i ON a.id = i.applicant_id
 GROUP BY LOWER(a.email)
HAVING COUNT(DISTINCT i.job_posting_id) > 1
 ORDER BY normalized_email;


-- ===========================================================================
-- QUESTION 4
-- For each recruiter, compute their Final-stage conversion rate:
--   passed Final-stage interviews  /  total Final-stage interviews.
-- Include only recruiters with at least 3 Final-stage interviews.
-- NULLIF guards against division by zero (impossible here due to HAVING,
-- but included as good practice).
-- ===========================================================================

SELECT r.id                                                    AS recruiter_id,
       r.name                                                  AS recruiter_name,
       COUNT(*)                                                AS total_final,
       SUM(CASE WHEN i.outcome = 'passed' THEN 1 ELSE 0 END)  AS passed_final,
       ROUND(
           CAST(SUM(CASE WHEN i.outcome = 'passed' THEN 1 ELSE 0 END) AS REAL)
           / NULLIF(COUNT(*), 0),
           2
       )                                                       AS conversion_rate
  FROM interviews i
  JOIN job_postings jp ON i.job_posting_id = jp.id
  JOIN recruiters r    ON jp.recruiter_id  = r.id
 WHERE i.stage = 'Final'
 GROUP BY r.id, r.name
HAVING COUNT(*) >= 3
 ORDER BY conversion_rate DESC, r.name;


-- ===========================================================================
-- QUESTION 5 (Bonus)
-- Using a window function, find the recruiter with the most successful
-- placements (passed Final-stage interviews) per department.
--
-- Tie-handling: RANK() is used so that if two recruiters in the same
-- department have the same number of successful placements, both are
-- returned (both receive rank 1).  Departments with zero successful
-- placements do not appear because there is nothing to rank.
-- ===========================================================================

WITH placement_counts AS (
    SELECT r.id                  AS recruiter_id,
           r.name                AS recruiter_name,
           jp.department,
           COUNT(*)              AS successful_placements
      FROM interviews i
      JOIN job_postings jp ON i.job_posting_id = jp.id
      JOIN recruiters r    ON jp.recruiter_id  = r.id
     WHERE i.stage   = 'Final'
       AND i.outcome = 'passed'
     GROUP BY r.id, r.name, jp.department
),
ranked AS (
    SELECT *,
           RANK() OVER (
               PARTITION BY department
               ORDER BY successful_placements DESC
           ) AS rnk
      FROM placement_counts
)
SELECT recruiter_id,
       recruiter_name,
       department,
       successful_placements
  FROM ranked
 WHERE rnk = 1
 ORDER BY department, recruiter_name;
