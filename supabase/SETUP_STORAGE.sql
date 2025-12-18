-- =====================================================
-- Supabase Storage Setup - Resume Upload Bucket
-- Run this in Supabase SQL Editor
-- =====================================================

-- Create storage bucket for resumes
INSERT INTO storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
VALUES (
  'resumes',
  'resumes',
  false, -- Private bucket
  10485760, -- 10MB limit
  ARRAY['application/pdf', 'application/msword', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document']
)
ON CONFLICT (id) DO NOTHING;

-- Verify setup
SELECT 
  'Storage bucket created successfully!' as status,
  id, 
  name, 
  public,
  file_size_limit,
  allowed_mime_types
FROM storage.buckets 
WHERE id = 'resumes';

SELECT 
  'Storage policies created:' as status,
  COUNT(*) as policy_count
FROM pg_policies 
WHERE schemaname = 'storage' 
  AND tablename = 'objects'
  AND policyname LIKE '%own%';
