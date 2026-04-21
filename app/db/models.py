"""Database table definitions and row mappers."""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class User:
    """User table row."""

    id: int
    user_id: str  # unique external identifier
    username: str
    api_key: str
    role: str  # 'admin' or 'user'
    created_at: datetime

    @classmethod
    def from_row(cls, row: tuple) -> "User":
        return cls(
            id=row[0],
            user_id=row[1],
            username=row[2],
            api_key=row[3],
            role=row[4],
            created_at=row[5],
        )


@dataclass
class Skill:
    """Skill table row."""

    id: int
    name: str
    description: str
    path: str  # Relative path to skill folder (e.g., "code-review")
    dependencies: list  # MCP dependencies
    created_at: Optional[datetime]
    updated_at: Optional[datetime]

    @classmethod
    def from_row(cls, row: tuple) -> "Skill":
        return cls(
            id=row[0],
            name=row[1],
            description=row[2],
            path=row[3],
            dependencies=row[4] if len(row) > 4 else [],
            created_at=row[5] if len(row) > 5 else None,
            updated_at=row[6] if len(row) > 6 else None,
        )


@dataclass
class UserSkill:
    """UserSkill junction table row."""

    user_id: int
    skill_id: int
    granted_at: datetime

    @classmethod
    def from_row(cls, row: tuple) -> "UserSkill":
        return cls(
            user_id=row[0],
            skill_id=row[1],
            granted_at=row[2],
        )


@dataclass
class SkillCall:
    """SkillCall audit table row."""

    id: int
    user_id: int
    skill_id: int
    call_time: datetime
    status: str  # 'success', 'failure', 'denied'
    error_message: Optional[str]
    duration_ms: int

    @classmethod
    def from_row(cls, row: tuple) -> "SkillCall":
        return cls(
            id=row[0],
            user_id=row[1],
            skill_id=row[2],
            call_time=row[3],
            status=row[4],
            error_message=row[5],
            duration_ms=row[6],
        )


# SQL for creating tables
CREATE_TABLES_SQL = """
CREATE TABLE IF NOT EXISTS users (
    id INT PRIMARY KEY AUTO_INCREMENT,
    user_id VARCHAR(100) UNIQUE NOT NULL,
    username VARCHAR(100) NOT NULL,
    api_key VARCHAR(128) UNIQUE NOT NULL,
    role ENUM('admin', 'user') DEFAULT 'user',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_api_key (api_key),
    INDEX idx_user_id (user_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS skills (
    id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(100) UNIQUE NOT NULL,
    description TEXT NOT NULL,
    path VARCHAR(500) NOT NULL,  -- Relative path to skill folder
    dependencies JSON,
    status ENUM('draft', 'active') DEFAULT 'draft',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_name (name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS user_skills (
    user_id INT NOT NULL,
    skill_id INT NOT NULL,
    granted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (user_id, skill_id),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (skill_id) REFERENCES skills(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

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
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
"""
