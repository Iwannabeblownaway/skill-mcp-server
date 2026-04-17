-- Migration: Add content_json column to skills table
ALTER TABLE skills ADD COLUMN content_json JSON AFTER version;
