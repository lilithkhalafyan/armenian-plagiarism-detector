"""Database helpers for the plagiarism detector."""

import json
import sqlite3
from typing import Dict

from config import DB_PATH, logger


def get_db() -> sqlite3.Connection:
    """Get database connection with row factory."""
    db = sqlite3.connect(DB_PATH)
    db.row_factory = sqlite3.Row
    return db


def init_db() -> None:
    """Initialize database with proper schema."""
    logger.info("🔄 Initializing database...")

    with get_db() as conn:
        c = conn.cursor()

        # Users table
        c.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                full_name TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                salt TEXT NOT NULL,
                role TEXT NOT NULL CHECK(role IN ('lecturer', 'student')),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_login TIMESTAMP,
                is_active INTEGER DEFAULT 1
            )
        ''')

        # Sessions table
        c.execute('''
            CREATE TABLE IF NOT EXISTS sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                upload_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                file_count INTEGER NOT NULL,
                theme TEXT,
                description TEXT,
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
            )
        ''')

        # Files table
        c.execute('''
            CREATE TABLE IF NOT EXISTS uploaded_files (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER NOT NULL,
                filename TEXT NOT NULL,
                stored_filename TEXT NOT NULL,
                upload_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                file_size INTEGER,
                word_count INTEGER,
                detected_theme TEXT,
                ai_score REAL,
                processed_text TEXT,
                FOREIGN KEY(session_id) REFERENCES sessions(id) ON DELETE CASCADE
            )
        ''')

        # Plagiarism results table
        c.execute('''
            CREATE TABLE IF NOT EXISTS plagiarism_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER NOT NULL,
                file1_id INTEGER NOT NULL,
                file2_id INTEGER NOT NULL,
                similarity_score REAL NOT NULL,
                basic_similarity REAL,
                keyword_similarity REAL,
                semantic_similarity REAL,
                plagiarism_level TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                details TEXT,
                FOREIGN KEY(session_id) REFERENCES sessions(id) ON DELETE CASCADE,
                FOREIGN KEY(file1_id) REFERENCES uploaded_files(id) ON DELETE CASCADE,
                FOREIGN KEY(file2_id) REFERENCES uploaded_files(id) ON DELETE CASCADE
            )
        ''')

        # Questions table
        c.execute('''
            CREATE TABLE IF NOT EXISTS questions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                session_id INTEGER,
                title TEXT NOT NULL,
                question TEXT NOT NULL,
                answer TEXT,
                status TEXT DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                answered_at TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
                FOREIGN KEY(session_id) REFERENCES sessions(id) ON DELETE CASCADE
            )
        ''')

        # Enhanced feedback table
        c.execute('''
            CREATE TABLE IF NOT EXISTS enhanced_feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                session_id INTEGER,
                subject TEXT NOT NULL,
                message TEXT NOT NULL,
                reply TEXT,
                status TEXT DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                replied_at TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
                FOREIGN KEY(session_id) REFERENCES sessions(id) ON DELETE CASCADE
            )
        ''')

        # Notifications table
        c.execute('''
            CREATE TABLE IF NOT EXISTS notifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                type TEXT NOT NULL,
                title TEXT NOT NULL,
                message TEXT NOT NULL,
                link TEXT,
                is_read INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
            )
        ''')

        # Submissions table
        c.execute('''
            CREATE TABLE IF NOT EXISTS submissions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                session_id INTEGER NOT NULL,
                title TEXT,
                description TEXT,
                submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
                FOREIGN KEY(session_id) REFERENCES sessions(id) ON DELETE CASCADE
            )
        ''')

        # Create indexes
        c.execute('CREATE INDEX IF NOT EXISTS idx_sessions_user ON sessions(user_id)')
        c.execute('CREATE INDEX IF NOT EXISTS idx_files_session ON uploaded_files(session_id)')
        c.execute('CREATE INDEX IF NOT EXISTS idx_results_session ON plagiarism_results(session_id)')
        c.execute('CREATE INDEX IF NOT EXISTS idx_notifications_user ON notifications(user_id, is_read)')

        conn.commit()

    logger.info("✅ Database initialized successfully")


def create_notification(user_id, type, title, message, link=None):
    """Create a notification for a user."""
    try:
        with get_db() as conn:
            c = conn.cursor()
            c.execute('''
                INSERT INTO notifications (user_id, type, title, message, link)
                VALUES (?, ?, ?, ?, ?)
            ''', (user_id, type, title, message, link))
            conn.commit()
    except Exception as e:
        logger.error(f"Error creating notification: {e}")


def record_session(user_id: int, file_count: int, theme: str = None, description: str = None) -> int:
    """Record a session in database."""
    with get_db() as conn:
        c = conn.cursor()
        c.execute('''
            INSERT INTO sessions (user_id, file_count, theme, description)
            VALUES (?, ?, ?, ?)
        ''', (user_id, file_count, theme, description))
        session_id = c.lastrowid
        conn.commit()
        return session_id


def record_file(session_id: int, filename: str, stored_filename: str, file_size: int,
                word_count: int, detected_theme: str = None, ai_score: float = None,
                processed_text: str = None) -> int:
    """Record an uploaded file."""
    with get_db() as conn:
        c = conn.cursor()
        c.execute('''
            INSERT INTO uploaded_files 
            (session_id, filename, stored_filename, file_size, word_count, 
             detected_theme, ai_score, processed_text)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (session_id, filename, stored_filename, file_size, word_count,
              detected_theme, ai_score, processed_text))
        file_id = c.lastrowid
        conn.commit()
        return file_id


def record_plagiarism_result(session_id: int, file1_id: int, file2_id: int,
                            similarities: Dict, level: str, details: Dict = None) -> int:
    """Record plagiarism comparison result."""
    with get_db() as conn:
        c = conn.cursor()
        c.execute('''
            INSERT INTO plagiarism_results 
            (session_id, file1_id, file2_id, similarity_score, basic_similarity, 
             keyword_similarity, semantic_similarity, plagiarism_level, details)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            session_id, file1_id, file2_id,
            float(similarities['combined_similarity']),
            float(similarities['basic_similarity']),
            float(similarities.get('tfidf_similarity', 0)),
            float(similarities['semantic_similarity']),
            level,
            json.dumps(details) if details else None
        ))
        result_id = c.lastrowid
        conn.commit()
        return result_id
