-- Database initialization script for skill-mcp-server
-- Creates all required tables matching the schema in docs/架构文档.md

-- Users table: stores user accounts and API keys
CREATE TABLE IF NOT EXISTS users (
    id INT PRIMARY KEY AUTO_INCREMENT,
    external_id VARCHAR(100) UNIQUE,
    username VARCHAR(100),
    api_key VARCHAR(64) UNIQUE NOT NULL,
    role ENUM('admin', 'user') DEFAULT 'user',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_api_key (api_key),
    INDEX idx_external_id (external_id)
);

-- Skills table: stores skill metadata and content
CREATE TABLE IF NOT EXISTS skills (
    id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(100) UNIQUE NOT NULL,
    description TEXT NOT NULL,
    path VARCHAR(500) NOT NULL,  -- Relative path to skill folder (e.g., "code-review")
    version VARCHAR(20) DEFAULT '1.0',
    content_json JSON,  -- JSON content of entire skill folder (files as key-value)
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_name (name)
);

-- User-skills junction table: maps which users have access to which skills
CREATE TABLE IF NOT EXISTS user_skills (
    user_id INT,
    skill_id INT,
    granted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (user_id, skill_id),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (skill_id) REFERENCES skills(id) ON DELETE CASCADE
);

-- Skill calls logging table: tracks all skill invocations
CREATE TABLE IF NOT EXISTS skill_calls (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    user_id INT NOT NULL,
    skill_id INT NOT NULL,
    call_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status ENUM('success', 'failure', 'denied') NOT NULL,
    error_message TEXT,
    duration_ms INT,
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (skill_id) REFERENCES skills(id),
    INDEX idx_user_time (user_id, call_time),
    INDEX idx_skill (skill_id)
);
