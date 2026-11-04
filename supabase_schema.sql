-- ==============================================================================
-- SUPABASE POSTGRESQL DATABASE SCHEMA
-- Arya by Mentoria - Autonomous AI Job Hunting Platform
-- ==============================================================================

-- 1. CANDIDATE PROFILES TABLE
CREATE TABLE IF NOT EXISTS public.profiles (
    id TEXT PRIMARY KEY,
    first_name TEXT NOT NULL,
    last_name TEXT,
    email TEXT,
    phone TEXT,
    linkedin_url TEXT,
    location TEXT,
    preferred_locations JSONB DEFAULT '[]'::jsonb,
    target_roles JSONB DEFAULT '[]'::jsonb,
    verified_skills JSONB DEFAULT '[]'::jsonb,
    min_desired_salary_usd NUMERIC DEFAULT 0,
    experiences JSONB DEFAULT '[]'::jsonb,
    education JSONB DEFAULT '[]'::jsonb,
    certifications JSONB DEFAULT '[]'::jsonb,
    raw_profile JSONB DEFAULT '{}'::jsonb,
    updated_at TIMESTAMPTZ DEFAULT TIMEZONE('utc'::text, NOW())
);

-- 2. JOBS TABLE (Real-Time Job Feed)
CREATE TABLE IF NOT EXISTS public.jobs (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    company TEXT NOT NULL,
    location TEXT,
    is_remote BOOLEAN DEFAULT FALSE,
    salary TEXT,
    match_score INTEGER DEFAULT 90,
    url TEXT UNIQUE NOT NULL,
    already_applied BOOLEAN DEFAULT FALSE,
    skills JSONB DEFAULT '[]'::jsonb,
    posted_time TEXT DEFAULT 'Recently active',
    created_at TIMESTAMPTZ DEFAULT TIMEZONE('utc'::text, NOW()),
    updated_at TIMESTAMPTZ DEFAULT TIMEZONE('utc'::text, NOW())
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_jobs_match_score ON public.jobs (match_score DESC);
CREATE INDEX IF NOT EXISTS idx_jobs_already_applied ON public.jobs (already_applied);
CREATE INDEX IF NOT EXISTS idx_jobs_created_at ON public.jobs (created_at DESC);

-- 3. APPLICATIONS LEDGER TABLE
CREATE TABLE IF NOT EXISTS public.applications (
    id TEXT PRIMARY KEY,
    job_id TEXT,
    company_name TEXT NOT NULL,
    job_title TEXT NOT NULL,
    job_url TEXT NOT NULL,
    location TEXT,
    salary TEXT,
    match_score INTEGER,
    relevance_score NUMERIC,
    status TEXT DEFAULT 'SUBMITTED',
    confirmation_id TEXT,
    applied_at TIMESTAMPTZ DEFAULT TIMEZONE('utc'::text, NOW()),
    notes TEXT,
    channel TEXT DEFAULT 'Arya Autonomous AI Multi-Agent',
    resume_version TEXT,
    created_at TIMESTAMPTZ DEFAULT TIMEZONE('utc'::text, NOW())
);

CREATE INDEX IF NOT EXISTS idx_applications_job_url ON public.applications (job_url);
CREATE INDEX IF NOT EXISTS idx_applications_created_at ON public.applications (created_at DESC);

-- 4. APPLICATION DRAFTS TABLE
CREATE TABLE IF NOT EXISTS public.drafts (
    id TEXT PRIMARY KEY,
    job_url TEXT,
    job_title TEXT NOT NULL,
    company TEXT NOT NULL,
    location TEXT,
    score NUMERIC,
    tailored_cv TEXT,
    status TEXT DEFAULT 'STAGED',
    created_at TIMESTAMPTZ DEFAULT TIMEZONE('utc'::text, NOW())
);

-- 5. INTERVIEWS & COMMUNICATIONS TABLE
CREATE TABLE IF NOT EXISTS public.interviews (
    id TEXT PRIMARY KEY,
    company TEXT NOT NULL,
    role TEXT NOT NULL,
    stage TEXT DEFAULT 'Invited',
    interview_date TIMESTAMPTZ,
    channel TEXT,
    notes TEXT,
    followup_status TEXT,
    created_at TIMESTAMPTZ DEFAULT TIMEZONE('utc'::text, NOW())
);

-- ==============================================================================
-- ROW LEVEL SECURITY (RLS) POLICIES
-- Allows anonymous and authenticated access via Supabase public anon key
-- ==============================================================================

ALTER TABLE public.profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.jobs ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.applications ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.drafts ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.interviews ENABLE ROW LEVEL SECURITY;

-- Profiles Policies
DROP POLICY IF EXISTS "Allow public read access on profiles" ON public.profiles;
CREATE POLICY "Allow public read access on profiles" ON public.profiles FOR SELECT USING (true);
DROP POLICY IF EXISTS "Allow public write access on profiles" ON public.profiles;
CREATE POLICY "Allow public write access on profiles" ON public.profiles FOR ALL USING (true) WITH CHECK (true);

-- Jobs Policies
DROP POLICY IF EXISTS "Allow public read access on jobs" ON public.jobs;
CREATE POLICY "Allow public read access on jobs" ON public.jobs FOR SELECT USING (true);
DROP POLICY IF EXISTS "Allow public write access on jobs" ON public.jobs;
CREATE POLICY "Allow public write access on jobs" ON public.jobs FOR ALL USING (true) WITH CHECK (true);

-- Applications Policies
DROP POLICY IF EXISTS "Allow public read access on applications" ON public.applications;
CREATE POLICY "Allow public read access on applications" ON public.applications FOR SELECT USING (true);
DROP POLICY IF EXISTS "Allow public write access on applications" ON public.applications;
CREATE POLICY "Allow public write access on applications" ON public.applications FOR ALL USING (true) WITH CHECK (true);

-- Drafts Policies
DROP POLICY IF EXISTS "Allow public read access on drafts" ON public.drafts;
CREATE POLICY "Allow public read access on drafts" ON public.drafts FOR SELECT USING (true);
DROP POLICY IF EXISTS "Allow public write access on drafts" ON public.drafts;
CREATE POLICY "Allow public write access on drafts" ON public.drafts FOR ALL USING (true) WITH CHECK (true);

-- Interviews Policies
DROP POLICY IF EXISTS "Allow public read access on interviews" ON public.interviews;
CREATE POLICY "Allow public read access on interviews" ON public.interviews FOR SELECT USING (true);
DROP POLICY IF EXISTS "Allow public write access on interviews" ON public.interviews;
CREATE POLICY "Allow public write access on interviews" ON public.interviews FOR ALL USING (true) WITH CHECK (true);

-- Enable Supabase Realtime for Jobs and Applications
ALTER PUBLICATION supabase_realtime ADD TABLE public.jobs;
ALTER PUBLICATION supabase_realtime ADD TABLE public.applications;
