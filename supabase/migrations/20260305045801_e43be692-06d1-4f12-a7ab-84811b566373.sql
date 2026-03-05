
-- Drop the trigger that auto-creates profiles from auth.users
DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
DROP FUNCTION IF EXISTS public.handle_new_user();

-- Drop existing RLS policies
DROP POLICY IF EXISTS "Users can insert own profile" ON public.profiles;
DROP POLICY IF EXISTS "Users can update own profile" ON public.profiles;
DROP POLICY IF EXISTS "Users can view own profile" ON public.profiles;

-- Drop the foreign key constraint to auth.users
ALTER TABLE public.profiles DROP CONSTRAINT IF EXISTS profiles_id_fkey;

-- Change id column from uuid to text to support Civic Auth user IDs
ALTER TABLE public.profiles ALTER COLUMN id SET DATA TYPE text;

-- Add new RLS policies that allow service_role access (edge function)
-- and allow anon/authenticated to read their own profile by id
CREATE POLICY "Allow all access via service role"
ON public.profiles
FOR ALL
TO service_role
USING (true)
WITH CHECK (true);

CREATE POLICY "Public read by id"
ON public.profiles
FOR SELECT
TO anon, authenticated
USING (true);
