ALTER TABLE public.profiles 
ADD COLUMN IF NOT EXISTS institution_name text,
ADD COLUMN IF NOT EXISTS annual_income numeric,
ADD COLUMN IF NOT EXISTS category text;