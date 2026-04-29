import sqlite3
from config import DB_PATH

SQL_CREATE_CONVERSATIONS = '''
CREATE TABLE IF NOT EXISTS conversations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id INTEGER NOT NULL,
    work_session_id INTEGER NOT NULL UNIQUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(student_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY(work_session_id) REFERENCES sessions(id) ON DELETE CASCADE
);
'''

SQL_CREATE_MESSAGES = '''
CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    conversation_id INTEGER NOT NULL,
    sender_id INTEGER NOT NULL,
    message TEXT NOT NULL,
    type TEXT NOT NULL DEFAULT 'text',
    is_read INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(conversation_id) REFERENCES conversations(id) ON DELETE CASCADE,
    FOREIGN KEY(sender_id) REFERENCES users(id) ON DELETE CASCADE
);
'''

SQL_CREATE_INDEXES = [
    'CREATE INDEX IF NOT EXISTS idx_messages_conversation ON messages(conversation_id)',
    'CREATE INDEX IF NOT EXISTS idx_messages_sender ON messages(sender_id)'
]


def migrate():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    c.execute(SQL_CREATE_CONVERSATIONS)
    c.execute(SQL_CREATE_MESSAGES)
    for sql in SQL_CREATE_INDEXES:
        c.execute(sql)

    c.execute("SELECT id FROM users WHERE role = 'lecturer' ORDER BY id LIMIT 1")
    lecturer_row = c.fetchone()
    lecturer_id = lecturer_row['id'] if lecturer_row else None

    c.execute('INSERT OR IGNORE INTO conversations (student_id, work_session_id) SELECT user_id, id FROM sessions')
    conn.commit()

    migrated_questions = 0
    c.execute('''
        SELECT id, user_id, session_id, question, answer, created_at, answered_at
        FROM questions
        WHERE session_id IS NOT NULL
    ''')
    questions = c.fetchall()
    for q in questions:
        c.execute('SELECT id FROM conversations WHERE work_session_id = ?', (q['session_id'],))
        conv = c.fetchone()
        if not conv:
            continue
        conv_id = conv['id']
        c.execute('''
            SELECT id FROM messages
            WHERE conversation_id = ? AND sender_id = ? AND type = 'question' AND message = ?
        ''', (conv_id, q['user_id'], q['question']))
        if not c.fetchone():
            c.execute('''
                INSERT INTO messages (conversation_id, sender_id, message, type, created_at)
                VALUES (?, ?, ?, 'question', ?)
            ''', (conv_id, q['user_id'], q['question'], q['created_at']))
            migrated_questions += 1
        if q['answer']:
            reply_sender_id = lecturer_id if lecturer_id else q['user_id']
            c.execute('''
                SELECT id FROM messages
                WHERE conversation_id = ? AND sender_id = ? AND type = 'answer' AND message = ?
            ''', (conv_id, reply_sender_id, q['answer']))
            if not c.fetchone():
                c.execute('''
                    INSERT INTO messages (conversation_id, sender_id, message, type, created_at)
                    VALUES (?, ?, ?, 'answer', ?)
                ''', (conv_id, reply_sender_id, q['answer'], q['answered_at'] or q['created_at']))
                migrated_questions += 1

    migrated_feedback = 0
    c.execute('''
        SELECT id, user_id, session_id, message, reply, created_at, replied_at
        FROM enhanced_feedback
        WHERE session_id IS NOT NULL
    ''')
    feedback_rows = c.fetchall()
    for fb in feedback_rows:
        c.execute('SELECT id FROM conversations WHERE work_session_id = ?', (fb['session_id'],))
        conv = c.fetchone()
        if not conv:
            continue
        conv_id = conv['id']
        c.execute('''
            SELECT id FROM messages
            WHERE conversation_id = ? AND sender_id = ? AND type = 'feedback' AND message = ?
        ''', (conv_id, fb['user_id'], fb['message']))
        if not c.fetchone():
            c.execute('''
                INSERT INTO messages (conversation_id, sender_id, message, type, created_at)
                VALUES (?, ?, ?, 'feedback', ?)
            ''', (conv_id, fb['user_id'], fb['message'], fb['created_at']))
            migrated_feedback += 1
        if fb['reply']:
            reply_sender_id = lecturer_id if lecturer_id else fb['user_id']
            c.execute('''
                SELECT id FROM messages
                WHERE conversation_id = ? AND sender_id = ? AND type = 'reply' AND message = ?
            ''', (conv_id, reply_sender_id, fb['reply']))
            if not c.fetchone():
                c.execute('''
                    INSERT INTO messages (conversation_id, sender_id, message, type, created_at)
                    VALUES (?, ?, ?, 'reply', ?)
                ''', (conv_id, reply_sender_id, fb['reply'], fb['replied_at'] or fb['created_at']))
                migrated_feedback += 1

    conn.commit()
    conn.close()

    print('Migration complete:')
    print(f'  conversations initialized')
    print(f'  questions -> messages migrated: {migrated_questions}')
    print(f'  enhanced_feedback -> messages migrated: {migrated_feedback}')
    print('If you want to inspect new messages, query the messages and conversations tables.')


if __name__ == '__main__':
    migrate()
