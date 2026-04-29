"""Student Works API - Messenger and file management."""

import os
from flask import Blueprint, request, jsonify, session, send_file
from db import get_db
from file_utils import load_text
from config import UPLOAD_FOLDER, logger
from similarity import highlight_word_level
from ai_detection import detect_ai_content

student_works_bp = Blueprint('student_works', __name__, url_prefix='/api/student-works')


@student_works_bp.route('/students', methods=['GET'])
def get_students_with_works():
    """Get all students who have uploaded files (lecturer only)."""
    if session.get('role') != 'lecturer':
        return jsonify({'success': False, 'error': 'Unauthorized'}), 403
    
    try:
        with get_db() as conn:
            c = conn.cursor()
            c.execute('''
                SELECT DISTINCT u.id, u.username, u.full_name, u.email,
                       MAX(s.upload_time) as last_activity
                FROM users u
                JOIN sessions s ON u.id = s.user_id
                WHERE u.role = 'student'
                GROUP BY u.id
                ORDER BY last_activity DESC
            ''')
            students = c.fetchall()
            result = []
            for s in students:
                result.append({
                    'id': s['id'],
                    'username': s['username'],
                    'full_name': s['full_name'],
                    'email': s['email'],
                    'last_activity': s['last_activity']
                })
            return jsonify({'success': True, 'students': result})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@student_works_bp.route('/students/<int:student_id>/works', methods=['GET'])
def get_student_works(student_id):
    """Get all uploaded files (sessions) for a specific student."""
    role = session.get('role')
    user_id = session.get('user_id')
    if role != 'lecturer' and user_id != student_id:
        return jsonify({'success': False, 'error': 'Unauthorized'}), 403
    
    try:
        with get_db() as conn:
            c = conn.cursor()
            c.execute('''
                SELECT s.id as session_id, s.upload_time, s.theme,
                       uf.id as file_id, uf.filename, uf.ai_score, uf.word_count
                FROM sessions s
                JOIN uploaded_files uf ON s.id = uf.session_id
                WHERE s.user_id = ?
                ORDER BY s.upload_time DESC
            ''', (student_id,))
            rows = c.fetchall()
            
            works = {}
            for row in rows:
                sid = row['session_id']
                if sid not in works:
                    works[sid] = {
                        'session_id': sid,
                        'upload_time': row['upload_time'],
                        'theme': row['theme'],
                        'files': []
                    }
                works[sid]['files'].append({
                    'file_id': row['file_id'],
                    'filename': row['filename'],
                    'ai_score': float(row['ai_score']) if row['ai_score'] else 0,
                    'word_count': row['word_count']
                })
            
            return jsonify({'success': True, 'works': list(works.values())})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@student_works_bp.route('/conversation/<int:work_session_id>', methods=['GET'])
def get_conversation(work_session_id):
    """Get all messages for a specific work session."""
    user_id = session.get('user_id')
    role = session.get('role')
    
    try:
        with get_db() as conn:
            c = conn.cursor()
            # Verify permission
            if role == 'lecturer':
                c.execute('SELECT user_id FROM sessions WHERE id = ?', (work_session_id,))
                sess = c.fetchone()
                if not sess:
                    return jsonify({'success': False, 'error': 'Session not found'}), 404
            else:
                c.execute('SELECT user_id FROM sessions WHERE id = ? AND user_id = ?', 
                         (work_session_id, user_id))
                if not c.fetchone():
                    return jsonify({'success': False, 'error': 'Access denied'}), 403
            
            # Get or create conversation
            c.execute('''
                INSERT OR IGNORE INTO conversations (student_id, work_session_id)
                SELECT user_id, ? FROM sessions WHERE id = ?
            ''', (work_session_id, work_session_id))
            conn.commit()
            
            c.execute('SELECT id FROM conversations WHERE work_session_id = ?', (work_session_id,))
            conv = c.fetchone()
            if not conv:
                return jsonify({'success': True, 'messages': [], 'conversation_id': None})
            
            c.execute('''
                SELECT m.*, u.full_name as sender_name, u.role as sender_role
                FROM messages m
                JOIN users u ON m.sender_id = u.id
                WHERE m.conversation_id = ?
                ORDER BY m.created_at ASC
            ''', (conv['id'],))
            messages = c.fetchall()
            
            msg_list = []
            for m in messages:
                msg_list.append({
                    'id': m['id'],
                    'sender_id': m['sender_id'],
                    'sender_name': m['sender_name'],
                    'sender_role': m['sender_role'],
                    'message': m['message'],
                    'type': m['type'],
                    'is_read': bool(m['is_read']),
                    'created_at': m['created_at']
                })
            
            return jsonify({'success': True, 'messages': msg_list, 'conversation_id': conv['id']})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@student_works_bp.route('/conversation/<int:work_session_id>/message', methods=['POST'])
def send_message(work_session_id):
    """Send a new message in a conversation."""
    user_id = session.get('user_id')
    role = session.get('role')
    data = request.json
    message = data.get('message', '').strip()
    msg_type = data.get('type', 'text')
    
    if not message:
        return jsonify({'success': False, 'error': 'Message cannot be empty'}), 400
    
    try:
        with get_db() as conn:
            c = conn.cursor()
            # Verify permission
            if role == 'lecturer':
                c.execute('SELECT user_id FROM sessions WHERE id = ?', (work_session_id,))
                sess = c.fetchone()
                if not sess:
                    return jsonify({'success': False, 'error': 'Session not found'}), 404
                student_id = sess['user_id']
            else:
                c.execute('SELECT user_id FROM sessions WHERE id = ? AND user_id = ?', 
                         (work_session_id, user_id))
                if not c.fetchone():
                    return jsonify({'success': False, 'error': 'Access denied'}), 403
                student_id = user_id
            
            # Get or create conversation
            c.execute('''
                INSERT OR IGNORE INTO conversations (student_id, work_session_id)
                VALUES (?, ?)
            ''', (student_id, work_session_id))
            conn.commit()
            
            c.execute('SELECT id FROM conversations WHERE work_session_id = ?', (work_session_id,))
            conv = c.fetchone()
            
            c.execute('''
                INSERT INTO messages (conversation_id, sender_id, message, type)
                VALUES (?, ?, ?, ?)
            ''', (conv['id'], user_id, message, msg_type))
            conn.commit()
            
            # Mark previous messages as read if lecturer is reading
            if role == 'lecturer':
                c.execute('''
                    UPDATE messages SET is_read = 1
                    WHERE conversation_id = ? AND sender_id != ?
                ''', (conv['id'], user_id))
                conn.commit()
            
            return jsonify({'success': True, 'message_id': c.lastrowid})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@student_works_bp.route('/file/<int:file_id>', methods=['GET'])
def get_file_content(file_id):
    """Get file text content for preview (lecturer or owner)."""
    user_id = session.get('user_id')
    role = session.get('role')
    
    try:
        with get_db() as conn:
            c = conn.cursor()
            c.execute('''
                SELECT uf.*, s.user_id as student_id
                FROM uploaded_files uf
                JOIN sessions s ON uf.session_id = s.id
                WHERE uf.id = ?
            ''', (file_id,))
            file = c.fetchone()
            if not file:
                return jsonify({'success': False, 'error': 'File not found'}), 404
            
            if role != 'lecturer' and file['student_id'] != user_id:
                return jsonify({'success': False, 'error': 'Access denied'}), 403
            
            filepath = os.path.join(UPLOAD_FOLDER, file['stored_filename'])
            full_text = load_text(filepath) or ''
            
            return jsonify({
                'success': True,
                'file': {
                    'id': file['id'],
                    'filename': file['filename'],
                    'ai_score': float(file['ai_score']) if file['ai_score'] else 0,
                    'word_count': file['word_count'],
                    'text_preview': full_text[:1000],
                    'full_text': full_text,
                    'upload_time': file['upload_time']
                }
            })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@student_works_bp.route('/download/<int:file_id>', methods=['GET'])
def download_file(file_id):
    """Download original file (lecturer or owner)."""
    user_id = session.get('user_id')
    role = session.get('role')
    
    with get_db() as conn:
        c = conn.cursor()
        c.execute('''
            SELECT uf.stored_filename, uf.filename, s.user_id as student_id
            FROM uploaded_files uf
            JOIN sessions s ON uf.session_id = s.id
            WHERE uf.id = ?
        ''', (file_id,))
        file = c.fetchone()
        if not file:
            return "File not found", 404
        
        if role != 'lecturer' and file['student_id'] != user_id:
            return "Access denied", 403
        
        filepath = os.path.join(UPLOAD_FOLDER, file['stored_filename'])
        return send_file(filepath, as_attachment=True, download_name=file['filename'])


@student_works_bp.route('/compare/<int:file_id1>/<int:file_id2>', methods=['GET'])
def compare_files(file_id1, file_id2):
    """Compare two files with word-level plagiarism highlighting."""
    user_id = session.get('user_id')
    role = session.get('role')
    
    try:
        with get_db() as conn:
            c = conn.cursor()
            
            # Get both files
            c.execute('''
                SELECT uf.*, s.user_id as student_id
                FROM uploaded_files uf
                JOIN sessions s ON uf.session_id = s.id
                WHERE uf.id = ?
            ''', (file_id1,))
            file1 = c.fetchone()
            
            c.execute('''
                SELECT uf.*, s.user_id as student_id
                FROM uploaded_files uf
                JOIN sessions s ON uf.session_id = s.id
                WHERE uf.id = ?
            ''', (file_id2,))
            file2 = c.fetchone()
            
            if not file1 or not file2:
                return jsonify({'success': False, 'error': 'One or both files not found'}), 404
            
            # Permission check: lecturer can compare any, student can compare their own
            if role != 'lecturer':
                if file1['student_id'] != user_id or file2['student_id'] != user_id:
                    return jsonify({'success': False, 'error': 'Access denied'}), 403
            
            # Load file contents
            filepath1 = os.path.join(UPLOAD_FOLDER, file1['stored_filename'])
            filepath2 = os.path.join(UPLOAD_FOLDER, file2['stored_filename'])
            
            text1 = load_text(filepath1) or ''
            text2 = load_text(filepath2) or ''
            
            # Get word-level highlighting
            highlighting = highlight_word_level(text1, text2)
            
            return jsonify({
                'success': True,
                'file1': {
                    'id': file1['id'],
                    'filename': file1['filename'],
                    'ai_score': float(file1['ai_score']) if file1['ai_score'] else 0
                },
                'file2': {
                    'id': file2['id'],
                    'filename': file2['filename'],
                    'ai_score': float(file2['ai_score']) if file2['ai_score'] else 0
                },
                'highlighting': highlighting
            })
    except Exception as e:
        logger.error(f"Error comparing files: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500