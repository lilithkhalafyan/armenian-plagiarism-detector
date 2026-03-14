# reset_db.py
import os
import sqlite3
import hashlib
import secrets

DB_PATH = 'plagiarism.db'

def hash_password(password, salt=None):
    """Hash password with PBKDF2"""
    if salt is None:
        salt = secrets.token_hex(16)
    
    key = hashlib.pbkdf2_hmac(
        'sha256',
        password.encode('utf-8'),
        salt.encode('utf-8'),
        100000,
        dklen=32
    )
    return key.hex(), salt

print("🗑️ Removing old database...")
if os.path.exists(DB_PATH):
    os.remove(DB_PATH)
    print("✅ Old database removed")

print("🔄 Creating new database...")
conn = sqlite3.connect(DB_PATH)
c = conn.cursor()

# Create tables
c.execute('''
    CREATE TABLE users (
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

# Create test users
print("👥 Creating test users...")

# Lecturer
password_hash, salt = hash_password('lecturer123')
c.execute('''
    INSERT INTO users (username, full_name, email, password_hash, salt, role)
    VALUES (?, ?, ?, ?, ?, ?)
''', ('lecturer', 'Test Lecturer', 'lecturer@example.com', password_hash, salt, 'lecturer'))
print("✅ Created lecturer: username='lecturer', password='lecturer123'")

# Student
password_hash, salt = hash_password('student123')
c.execute('''
    INSERT INTO users (username, full_name, email, password_hash, salt, role)
    VALUES (?, ?, ?, ?, ?, ?)
''', ('student', 'Test Student', 'student@example.com', password_hash, salt, 'student'))
print("✅ Created student: username='student', password='student123'")

# Create other tables
c.execute('''
    CREATE TABLE sessions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        upload_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        file_count INTEGER NOT NULL,
        theme TEXT,
        description TEXT,
        FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
    )
''')

c.execute('''
    CREATE TABLE uploaded_files (
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

c.execute('''
    CREATE TABLE plagiarism_results (
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

c.execute('''
    CREATE TABLE feedback (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id INTEGER NOT NULL,
        from_user_id INTEGER NOT NULL,
        to_user_id INTEGER NOT NULL,
        message TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        is_read INTEGER DEFAULT 0,
        reply_to INTEGER,
        FOREIGN KEY(session_id) REFERENCES sessions(id) ON DELETE CASCADE,
        FOREIGN KEY(from_user_id) REFERENCES users(id) ON DELETE CASCADE,
        FOREIGN KEY(to_user_id) REFERENCES users(id) ON DELETE CASCADE,
        FOREIGN KEY(reply_to) REFERENCES feedback(id) ON DELETE SET NULL
    )
''')

c.execute('''
    CREATE TABLE activity_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        action TEXT NOT NULL,
        details TEXT,
        ip_address TEXT,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
    )
''')

# Create indexes
c.execute('CREATE INDEX idx_sessions_user ON sessions(user_id)')
c.execute('CREATE INDEX idx_files_session ON uploaded_files(session_id)')
c.execute('CREATE INDEX idx_results_session ON plagiarism_results(session_id)')
c.execute('CREATE INDEX idx_feedback_session ON feedback(session_id)')

conn.commit()
conn.close()

print("✅ Database created successfully!")
print("\n📊 Test Users:")
print("   Lecturer: username='lecturer', password='lecturer123'")
print("   Student:  username='student', password='student123'")