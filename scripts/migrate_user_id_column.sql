-- Migration: Rename external_id to user_id in users table
-- This aligns with the newer code that uses user_id instead of external_id

-- Check if external_id column exists
-- If it does and user_id doesn't, rename it
ALTER TABLE users ADD COLUMN IF NOT EXISTS user_id VARCHAR(100) UNIQUE AFTER id;

-- Copy data from external_id to user_id if user_id is NULL
UPDATE users SET user_id = external_id WHERE user_id IS NULL AND external_id IS NOT NULL;

-- Drop the old external_id column if user_id now exists
-- ALTER TABLE users DROP COLUMN IF EXISTS external_id;
-- Note: We keep external_id as backup for now, can drop after verification
