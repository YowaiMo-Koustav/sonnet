
-- Drop all existing policies on profiles
DROP POLICY IF EXISTS "Public read by id" ON public.profiles;
DROP POLICY IF EXISTS "Allow all access via service role" ON public.profiles;
DROP POLICY IF EXISTS "Allow owner to read profile" ON public.profiles;
DROP POLICY IF EXISTS "Allow owner to create profile" ON public.profiles;
DROP POLICY IF EXISTS "Allow owner to update profile" ON public.profiles;
DROP POLICY IF EXISTS "Allow owner to delete profile" ON public.profiles;

-- Ensure RLS is enabled
ALTER TABLE public.profiles ENABLE ROW LEVEL SECURITY;

-- No permissive policies for anon/authenticated users
-- All access goes through edge functions using service_role key (bypasses RLS)
-- This ensures zero direct access from the client
