
-- Drop existing misleading policies
DROP POLICY IF EXISTS "Allow all access via service role" ON public.profiles;
DROP POLICY IF EXISTS "Public read by id" ON public.profiles;

-- RLS remains enabled with NO permissive policies = deny all direct access
-- Service role (used by edge functions) bypasses RLS automatically
-- This is the most secure configuration for Civic Auth integration
