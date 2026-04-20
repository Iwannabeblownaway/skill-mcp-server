-- Migration: Remove version and content_json columns from skills table
-- These fields are no longer used

ALTER TABLE skills DROP COLUMN IF EXISTS version;
ALTER TABLE skills DROP COLUMN IF EXISTS content_json;
