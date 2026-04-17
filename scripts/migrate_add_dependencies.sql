-- Migration: Add dependencies column to skills table
-- Description: Store MCP URL dependencies for skills (extracted from mcp_config or SKILL.md frontmatter)

ALTER TABLE skills ADD COLUMN dependencies JSON AFTER content_json;

-- Index for faster lookups (optional, depends on query patterns)
-- CREATE INDEX idx_skills_dependencies ON skills(dependencies);

-- Backfill existing skills with empty array
UPDATE skills SET dependencies = '[]' WHERE dependencies IS NULL;
