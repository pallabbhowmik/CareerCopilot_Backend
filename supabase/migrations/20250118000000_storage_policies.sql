-- =====================================================
-- STORAGE SETUP FOR RESUMES
-- =====================================================

-- Note: Create the 'resumes' bucket manually in Supabase Dashboard first:
-- Dashboard → Storage → New bucket
-- Name: resumes
-- Public: NO (private)
-- Allowed MIME types: application/pdf, application/msword, application/vnd.openxmlformats-officedocument.wordprocessingml.document
-- Max file size: 10485760 (10MB)

-- =====================================================
-- ROW LEVEL SECURITY POLICIES FOR STORAGE
-- =====================================================

-- Users can only upload resumes to their own folder (user_id/filename)
CREATE POLICY "Users can upload own resumes"
ON storage.objects FOR INSERT
TO authenticated
WITH CHECK (
  bucket_id = 'resumes' 
  AND auth.uid()::text = (storage.foldername(name))[1]
);

-- Users can only read their own resumes
CREATE POLICY "Users can read own resumes"
ON storage.objects FOR SELECT
TO authenticated
USING (
  bucket_id = 'resumes' 
  AND auth.uid()::text = (storage.foldername(name))[1]
);

-- Users can only update their own resumes
CREATE POLICY "Users can update own resumes"
ON storage.objects FOR UPDATE
TO authenticated
USING (
  bucket_id = 'resumes' 
  AND auth.uid()::text = (storage.foldername(name))[1]
);

-- Users can only delete their own resumes
CREATE POLICY "Users can delete own resumes"
ON storage.objects FOR DELETE
TO authenticated
USING (
  bucket_id = 'resumes' 
  AND auth.uid()::text = (storage.foldername(name))[1]
);

-- =====================================================
-- VERIFICATION
-- =====================================================

SELECT 'Storage policies created successfully!' as status;

-- Show all storage policies
SELECT schemaname, tablename, policyname, cmd, qual 
FROM pg_policies 
WHERE schemaname = 'storage' 
  AND tablename = 'objects'
ORDER BY policyname;
