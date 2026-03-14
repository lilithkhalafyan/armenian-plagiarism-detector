"""
Armenian Plagiarism Detection System - COMPLETE FIXED VERSION
All bugs fixed, highlighting working properly
"""

import json
import os
import re
import traceback
import uuid
from datetime import datetime, timedelta

from flask import Flask, request, jsonify, send_from_directory, session, make_response
from flask_cors import CORS
from werkzeug.utils import secure_filename

from ai_detection import detect_ai_content
from auth import (hash_password, login_required, lecturer_required,
                  student_required, verify_password)
from config import (MODEL_AVAILABLE, SYNONYMS, STOPWORDS, THEME_KEYWORDS,
                    UPLOAD_FOLDER, logger)
from db import (create_notification, get_db, init_db, record_file,
                record_plagiarism_result, record_session)
from file_utils import (allowed_file, detect_theme, extract_keywords, load_text,
                        preprocess_text)
from similarity import (calculate_enhanced_similarity, get_plagiarism_level,
                        highlight_word_level)

# ==================================================
# APP CONFIGURATION
# ==================================================
app = Flask(__name__, static_folder='.', static_url_path='')
app.secret_key = os.urandom(32).hex()
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SECURE'] = False
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=2)
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100MB limit
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['ALLOWED_EXTENSIONS'] = {'txt', 'pdf', 'doc', 'docx', 'rtf'}

# ==================================================
# CORS CONFIGURATION
# ==================================================
CORS(app, resources={r"/api/*": {
    "origins": ["http://localhost:5000", "http://127.0.0.1:5000"],
    "supports_credentials": True,
    "allow_headers": ["Content-Type", "Authorization"],
    "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    "max_age": 3600
}})

# ==================================================



# ==================================================
# AI DETECTION DETAILS ENDPOINT - NEW!
# ==================================================
@app.route('/api/ai-details/<int:session_id>/<path:filename>', methods=['GET'])
@login_required
def get_ai_details(session_id, filename):
    """Get detailed AI analysis with highlighted sentences"""
    try:
        with get_db() as conn:
            c = conn.cursor()
            
            # Get file from database
            c.execute('''
                SELECT * FROM uploaded_files 
                WHERE session_id = ? AND filename = ?
            ''', (session_id, filename))
            file = c.fetchone()
            
            if not file:
                return jsonify({'success': False, 'error': 'File not found'}), 404
            
            # Load file content
            filepath = os.path.join(UPLOAD_FOLDER, file['stored_filename'])
            text = load_text(filepath)
            
            # Get detailed AI analysis with sentence-level highlighting
            ai_result = detect_ai_content(text, detailed=True)
            
            # Also get plagiarism context if available (to show both)
            c.execute('''
                SELECT pr.*, uf1.filename as file1_name, uf2.filename as file2_name
                FROM plagiarism_results pr
                JOIN uploaded_files uf1 ON pr.file1_id = uf1.id
                JOIN uploaded_files uf2 ON pr.file2_id = uf2.id
                WHERE (uf1.id = ? OR uf2.id = ?) AND pr.session_id = ?
            ''', (file['id'], file['id'], session_id))
            
            plagiarism_results = c.fetchall()
            
            return jsonify({
                'success': True,
                'filename': filename,
                'ai_analysis': ai_result,
                'plagiarism_context': [dict(r) for r in plagiarism_results] if plagiarism_results else []
            })
            
    except Exception as e:
        logger.error(f"Error getting AI details: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/users/students', methods=['GET', 'OPTIONS'])
@lecturer_required
def get_students():
    """Get all students (lecturer only)"""
    if request.method == 'OPTIONS':
        return _build_cors_response()
    
    try:
        with get_db() as conn:
            c = conn.cursor()
            c.execute('''
                SELECT id, username, full_name, email, created_at, last_login
                FROM users 
                WHERE role = 'student' AND is_active = 1
                ORDER BY full_name
            ''')
            
            students = c.fetchall()
            
            result = []
            for s in students:
                result.append({
                    'id': s['id'],
                    'username': s['username'],
                    'full_name': s['full_name'],
                    'email': s['email'],
                    'created_at': s['created_at'],
                    'last_login': s['last_login']
                })
            
            return jsonify({
                'success': True,
                'students': result,
                'total': len(result)
            })
            
    except Exception as e:
        logger.error(f"Error getting students: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/register', methods=['POST', 'OPTIONS'])
def register():
    if request.method == 'OPTIONS':
        return _build_cors_response()
    
    data = request.json
    required = ['username', 'full_name', 'email', 'password', 'role']
    
    if not all(data.get(field) for field in required):
        return jsonify({'success': False, 'error': 'All fields are required'}), 400
    
    if data['role'] not in ['lecturer', 'student']:
        return jsonify({'success': False, 'error': 'Invalid role'}), 400
    
    if not re.match(r'^[^@]+@[^@]+\.[^@]+$', data['email']):
        return jsonify({'success': False, 'error': 'Invalid email format'}), 400
    
    if len(data['password']) < 6:
        return jsonify({'success': False, 'error': 'Password must be at least 6 characters'}), 400
    
    try:
        with get_db() as conn:
            c = conn.cursor()
            
            c.execute('SELECT id FROM users WHERE username = ? OR email = ?', 
                     (data['username'], data['email']))
            if c.fetchone():
                return jsonify({'success': False, 'error': 'Username or email already exists'}), 400
            
            password_hash, salt = hash_password(data['password'])
            
            c.execute('''
                INSERT INTO users (username, full_name, email, password_hash, salt, role)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (data['username'], data['full_name'], data['email'], 
                  password_hash, salt, data['role']))
            
            conn.commit()
            logger.info(f"✅ User registered: {data['username']}")
            
            return jsonify({'success': True, 'message': 'Registration successful'})
            
    except Exception as e:
        logger.error(f"Registration error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/login', methods=['POST', 'OPTIONS'])
def login():
    if request.method == 'OPTIONS':
        return _build_cors_response()
    
    data = request.json
    username = data.get('username')
    password = data.get('password')
    
    if not username or not password:
        return jsonify({'success': False, 'error': 'Username and password required'}), 400
    
    try:
        with get_db() as conn:
            c = conn.cursor()
            
            c.execute('''
                SELECT id, username, full_name, email, password_hash, salt, role 
                FROM users WHERE username = ? AND is_active = 1
            ''', (username,))
            
            user = c.fetchone()
            
            if not user or not verify_password(password, user['password_hash'], user['salt']):
                return jsonify({'success': False, 'error': 'Invalid username or password'}), 401
            
            c.execute('UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE id = ?', (user['id'],))
            conn.commit()
            
            session.clear()
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['role'] = user['role']
            session.permanent = True
            
            logger.info(f"✅ User logged in: {username}")
            
            return jsonify({
                'success': True,
                'user': {
                    'id': user['id'],
                    'username': user['username'],
                    'full_name': user['full_name'],
                    'email': user['email'],
                    'role': user['role']
                }
            })
            
    except Exception as e:
        logger.error(f"Login error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/logout', methods=['POST', 'OPTIONS'])
def logout():
    if request.method == 'OPTIONS':
        return _build_cors_response()
    
    session.clear()
    return jsonify({'success': True})

@app.route('/api/current-user', methods=['GET', 'OPTIONS'])
def current_user():
    if request.method == 'OPTIONS':
        return _build_cors_response()
    
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'success': False, 'user': None})
    
    try:
        with get_db() as conn:
            c = conn.cursor()
            c.execute('''
                SELECT id, username, full_name, email, role, created_at, last_login
                FROM users WHERE id = ?
            ''', (user_id,))
            
            user = c.fetchone()
            if user:
                return jsonify({
                    'success': True,
                    'user': {
                        'id': user['id'],
                        'username': user['username'],
                        'full_name': user['full_name'],
                        'email': user['email'],
                        'role': user['role'],
                        'created_at': user['created_at'],
                        'last_login': user['last_login']
                    }
                })
    except Exception as e:
        logger.error(f"Error getting current user: {e}")
    
    return jsonify({'success': False, 'user': None})

# ==================================================
# API ENDPOINTS - PLAGIARISM CHECK
# ==================================================
@app.route('/api/armenian-check', methods=['POST', 'OPTIONS'])
@login_required
def armenian_plagiarism_check():
    if request.method == 'OPTIONS':
        return _build_cors_response()
    
    try:
        user_id = session['user_id']
        user_role = session.get('role', 'student')
        
        if 'files' not in request.files:
            return jsonify({"error": "No files uploaded"}), 400

        files = request.files.getlist('files')

        if len(files) < 2:
            return jsonify({"error": "Please upload at least 2 files"}), 400

        uploaded_files = []
        problematic_files = []

        for file in files:
            if file and allowed_file(file.filename):
                try:
                    file.seek(0, os.SEEK_END)
                    file_size = file.tell()
                    file.seek(0)
                    
                    if file_size == 0:
                        problematic_files.append({
                            'name': file.filename,
                            'reason': 'File is empty'
                        })
                        continue
                    
                    if file_size > 100 * 1024 * 1024:  # 100MB
                        problematic_files.append({
                            'name': file.filename,
                            'reason': 'File too large (max 100MB)'
                        })
                        continue
                    
                    safe_name = secure_filename(file.filename)
                    stored_name = f"{uuid.uuid4().hex}_{safe_name}"
                    filepath = os.path.join(UPLOAD_FOLDER, stored_name)
                    file.save(filepath)
                    
                    # Extract text
                    text = load_text(filepath)
                    if not text or len(text.strip()) < 50:
                        problematic_files.append({
                            'name': file.filename,
                            'reason': 'Could not extract text or text too short'
                        })
                        os.remove(filepath)
                        continue
                    
                    uploaded_files.append({
                        "original_name": file.filename,
                        "stored_name": stored_name,
                        "path": filepath,
                        "size": file_size
                    })
                    
                except Exception as e:
                    logger.error(f"Error processing file {file.filename}: {e}")
                    problematic_files.append({
                        'name': file.filename,
                        'reason': f'Error: {str(e)}'
                    })
        
        if len(uploaded_files) < 2:
            return jsonify({
                "error": "Not enough valid files",
                "problematic_files": problematic_files
            }), 400
        
        # Process files
        all_text = ""
        file_data = []
        
        for uf in uploaded_files:
            text = load_text(uf['path'])
            if text:
                file_data.append({
                    "name": uf['original_name'],
                    "text": text,
                    "path": uf['path'],
                    "size": uf['size']
                })
                all_text += text + " "
        
        # Detect main theme
        themes = detect_theme(all_text)
        main_theme = themes[0][0] if themes else "general"
        
        # Create session
        session_id = record_session(user_id, len(file_data), main_theme)
        
        # Process each file
        file_records = []
        file_info = []
        ai_analysis = {}
        theme_analysis = {}
        
        for fd in file_data:
            processed = preprocess_text(fd['text'])
            word_count = len(fd['text'].split())
            
            # Detect theme for individual file
            file_themes = detect_theme(fd['text'])
            theme_analysis[fd['name']] = [
                {'theme': t[0], 'percentage': float(t[1]['percentage'])} 
                for t in file_themes
            ]
            
            # AI detection
            ai_result = detect_ai_content(fd['text'], detailed=(user_role == 'lecturer'))
            ai_analysis[fd['name']] = ai_result
            
            # Save to database
            file_id = record_file(
                session_id,
                fd['name'],
                os.path.basename(fd['path']),
                fd['size'],
                word_count,
                file_themes[0][0] if file_themes else None,
                float(ai_result['ai_percentage']),
                processed[:1000]
            )
            
            file_records.append({
                "id": file_id,
                "name": fd['name'],
                "word_count": word_count,
                "ai_score": ai_result['ai_percentage'],
                "themes": file_themes
            })
            
            file_info.append({
                "name": fd['name'],
                "text": fd['text'],
                "id": file_id
            })
        
        # Compare all pairs
        results = []
        all_keywords = {}
        
        for i in range(len(file_info)):
            for j in range(i + 1, len(file_info)):
                similarities = calculate_enhanced_similarity(
                    file_info[i]["text"],
                    file_info[j]["text"]
                )
                
                level = get_plagiarism_level(similarities['combined_similarity'])
                
                # For lecturers, include detailed highlighting
                details = None
                if user_role == 'lecturer':
                    details = highlight_word_level(
                        file_info[i]["text"],
                        file_info[j]["text"]
                    )
                
                record_plagiarism_result(
                    session_id,
                    file_info[i]['id'],
                    file_info[j]['id'],
                    similarities,
                    level,
                    details
                )
                
                result_item = {
                    "file1": file_info[i]["name"],
                    "file2": file_info[j]["name"],
                    "similarity": float(similarities['combined_similarity']),
                    "basic_similarity": float(similarities['basic_similarity']),
                    "keyword_similarity": float(similarities['tfidf_similarity']),
                    "semantic_similarity": float(similarities['semantic_similarity']),
                    "plagiarism_level": level
                }
                
                if user_role == 'lecturer' and details:
                    result_item['highlighting'] = details
                
                results.append(result_item)
                
                all_keywords[file_info[i]["name"]] = extract_keywords(file_info[i]["text"])
                all_keywords[file_info[j]["name"]] = extract_keywords(file_info[j]["text"])
        
        # Find highest plagiarism
        highest = max(results, key=lambda x: x["similarity"]) if results else None
        
        logger.info(f"✅ Plagiarism check complete for session {session_id}")
        
        return jsonify({
            "success": True,
            "session_id": session_id,
            "total_files": len(file_info),
            "results": results,
            "highest_plagiarism": highest,
            "keywords": all_keywords,
            "file_names": [f["name"] for f in file_info],
            "file_records": file_records,
            "theme_analysis": theme_analysis,
            "main_theme": main_theme,
            "ai_analysis": ai_analysis,
            "problematic_files": problematic_files,
            "user_role": user_role
        })
        
    except Exception as e:
        logger.error(f"Error in plagiarism check: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

# ==================================================
# API ENDPOINTS - HISTORY
# ==================================================
@app.route('/api/history', methods=['GET', 'OPTIONS'])
@login_required
def get_history():
    """Get user's session history."""
    if request.method == 'OPTIONS':
        return _build_cors_response()
    
    user_id = session['user_id']
    page = int(request.args.get('page', 0))
    limit = 10
    offset = page * limit
    
    try:
        with get_db() as conn:
            c = conn.cursor()
            
            c.execute('''
                SELECT s.*, 
                       COUNT(DISTINCT uf.id) as file_count,
                       COUNT(DISTINCT pr.id) as result_count,
                       MAX(pr.similarity_score) as max_similarity
                FROM sessions s
                LEFT JOIN uploaded_files uf ON s.id = uf.session_id
                LEFT JOIN plagiarism_results pr ON s.id = pr.session_id
                WHERE s.user_id = ?
                GROUP BY s.id
                ORDER BY s.upload_time DESC
                LIMIT ? OFFSET ?
            ''', (user_id, limit, offset))
            
            sessions = c.fetchall()
            
            history = []
            for s in sessions:
                history.append({
                    'id': s['id'],
                    'upload_time': s['upload_time'],
                    'file_count': s['file_count'],
                    'result_count': s['result_count'],
                    'max_similarity': float(s['max_similarity']) if s['max_similarity'] else 0,
                    'theme': s['theme']
                })
            
            return jsonify({
                'success': True,
                'history': history,
                'page': page,
                'has_more': len(history) == limit
            })
            
    except Exception as e:
        logger.error(f"Error loading history: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/history/<int:session_id>', methods=['GET', 'OPTIONS'])
@login_required
def get_session_results(session_id):
    """Get detailed results for a specific session."""
    if request.method == 'OPTIONS':
        return _build_cors_response()
    
    user_id = session['user_id']
    user_role = session.get('role', 'student')
    
    try:
        with get_db() as conn:
            c = conn.cursor()
            
            c.execute('SELECT user_id FROM sessions WHERE id = ?', (session_id,))
            sess = c.fetchone()
            if not sess or (sess['user_id'] != user_id and user_role != 'lecturer'):
                return jsonify({'success': False, 'error': 'Session not found'}), 404
            
            # Get files
            c.execute('''
                SELECT * FROM uploaded_files 
                WHERE session_id = ?
            ''', (session_id,))
            files = c.fetchall()
            
            # Get results
            c.execute('''
                SELECT pr.*, 
                       uf1.filename as file1_name,
                       uf2.filename as file2_name
                FROM plagiarism_results pr
                JOIN uploaded_files uf1 ON pr.file1_id = uf1.id
                JOIN uploaded_files uf2 ON pr.file2_id = uf2.id
                WHERE pr.session_id = ?
            ''', (session_id,))
            
            results = c.fetchall()
            
            formatted_results = []
            for r in results:
                result_item = {
                    'file1': r['file1_name'],
                    'file2': r['file2_name'],
                    'similarity': float(r['similarity_score']),
                    'basic_similarity': float(r['basic_similarity']) if r['basic_similarity'] else 0,
                    'keyword_similarity': float(r['keyword_similarity']) if r['keyword_similarity'] else 0,
                    'semantic_similarity': float(r['semantic_similarity']) if r['semantic_similarity'] else 0,
                    'plagiarism_level': r['plagiarism_level']
                }
                
                # Include highlighting details for lecturers - FIXED null check
                if r['details'] and user_role == 'lecturer':
                    try:
                        result_item['highlighting'] = json.loads(r['details'])
                    except:
                        result_item['highlighting'] = {'file1': [], 'file2': []}
                
                formatted_results.append(result_item)
            
            # Format files
            file_list = []
            for f in files:
                file_list.append({
                    'id': f['id'],
                    'filename': f['filename'],
                    'stored_filename': f['stored_filename'],
                    'file_size': f['file_size'],
                    'word_count': f['word_count'],
                    'detected_theme': f['detected_theme'],
                    'ai_score': float(f['ai_score']) if f['ai_score'] else 0
                })
            
            return jsonify({
                'success': True,
                'session_id': session_id,
                'results': formatted_results,
                'files': file_list
            })
            
    except Exception as e:
        logger.error(f"Error loading session {session_id}: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

# ==================================================
# API ENDPOINTS - NOTIFICATIONS
# ==================================================
@app.route('/api/notifications', methods=['GET', 'OPTIONS'])
@login_required
def get_notifications():
    """Get user notifications."""
    if request.method == 'OPTIONS':
        return _build_cors_response()
    
    user_id = session['user_id']
    
    try:
        with get_db() as conn:
            c = conn.cursor()
            c.execute('''
                SELECT * FROM notifications 
                WHERE user_id = ? 
                ORDER BY created_at DESC 
                LIMIT 50
            ''', (user_id,))
            
            notifications = c.fetchall()
            
            result = []
            for n in notifications:
                result.append({
                    'id': n['id'],
                    'type': n['type'],
                    'title': n['title'],
                    'message': n['message'],
                    'link': n['link'],
                    'is_read': bool(n['is_read']),
                    'created_at': n['created_at']
                })
            
            c.execute('SELECT COUNT(*) as unread FROM notifications WHERE user_id = ? AND is_read = 0', (user_id,))
            unread_count = c.fetchone()['unread']
            
            return jsonify({
                'success': True, 
                'notifications': result,
                'unread_count': unread_count
            })
            
    except Exception as e:
        logger.error(f"Error getting notifications: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/notifications/<int:notification_id>/read', methods=['POST', 'OPTIONS'])
@login_required
def mark_notification_read(notification_id):
    """Mark notification as read."""
    if request.method == 'OPTIONS':
        return _build_cors_response()
    
    user_id = session['user_id']
    
    try:
        with get_db() as conn:
            c = conn.cursor()
            c.execute('''
                UPDATE notifications 
                SET is_read = 1 
                WHERE id = ? AND user_id = ?
            ''', (notification_id, user_id))
            conn.commit()
            
            return jsonify({'success': True})
            
    except Exception as e:
        logger.error(f"Error marking notification read: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/notifications/read-all', methods=['POST', 'OPTIONS'])
@login_required
def mark_all_notifications_read():
    """Mark all notifications as read."""
    if request.method == 'OPTIONS':
        return _build_cors_response()
    
    user_id = session['user_id']
    
    try:
        with get_db() as conn:
            c = conn.cursor()
            c.execute('''
                UPDATE notifications 
                SET is_read = 1 
                WHERE user_id = ? AND is_read = 0
            ''', (user_id,))
            conn.commit()
            
            return jsonify({'success': True})
            
    except Exception as e:
        logger.error(f"Error marking all notifications read: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

# ==================================================
# API ENDPOINTS - QUESTIONS
# ==================================================
@app.route('/api/questions', methods=['POST', 'OPTIONS'])
@student_required
def ask_question():
    """Student asks a question."""
    if request.method == 'OPTIONS':
        return _build_cors_response()
    
    user_id = session['user_id']
    data = request.json
    
    title = data.get('title', '').strip()
    question = data.get('question', '').strip()
    session_id = data.get('session_id')
    
    if not title or not question:
        return jsonify({'success': False, 'error': 'Title and question required'}), 400
    
    try:
        with get_db() as conn:
            c = conn.cursor()
            c.execute('''
                INSERT INTO questions (user_id, session_id, title, question, status)
                VALUES (?, ?, ?, ?, 'pending')
            ''', (user_id, session_id, title, question))
            
            question_id = c.lastrowid
            conn.commit()
            
            # Notify lecturers
            c.execute('SELECT id FROM users WHERE role = "lecturer"')
            lecturers = c.fetchall()
            for lecturer in lecturers:
                create_notification(
                    lecturer['id'],
                    'question',
                    'New Question',
                    f'Student asked: {title}',
                    '/lecturer.html?tab=questions'
                )
            
            return jsonify({'success': True, 'question_id': question_id})
            
    except Exception as e:
        logger.error(f"Error asking question: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/questions', methods=['GET', 'OPTIONS'])
@login_required
def get_questions():
    """Get questions."""
    if request.method == 'OPTIONS':
        return _build_cors_response()
    
    user_id = session['user_id']
    role = session.get('role', 'student')
    
    try:
        with get_db() as conn:
            c = conn.cursor()
            
            if role == 'lecturer':
                c.execute('''
                    SELECT q.*, u.username, u.full_name 
                    FROM questions q
                    JOIN users u ON q.user_id = u.id
                    ORDER BY 
                        CASE q.status 
                            WHEN 'pending' THEN 1
                            WHEN 'answered' THEN 2
                            ELSE 3
                        END,
                        q.created_at DESC
                ''')
            else:
                c.execute('''
                    SELECT q.*, u.username, u.full_name 
                    FROM questions q
                    JOIN users u ON q.user_id = u.id
                    WHERE q.user_id = ?
                    ORDER BY q.created_at DESC
                ''', (user_id,))
            
            questions = c.fetchall()
            
            result = []
            for q in questions:
                result.append({
                    'id': q['id'],
                    'user_id': q['user_id'],
                    'username': q['username'],
                    'full_name': q['full_name'],
                    'title': q['title'],
                    'question': q['question'],
                    'answer': q['answer'],
                    'status': q['status'],
                    'created_at': q['created_at']
                })
            
            return jsonify({'success': True, 'questions': result})
            
    except Exception as e:
        logger.error(f"Error getting questions: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/questions/count', methods=['GET', 'OPTIONS'])
@lecturer_required
def get_questions_count():
    """Get count of pending questions."""
    if request.method == 'OPTIONS':
        return _build_cors_response()
    
    try:
        conn = get_db()
        c = conn.cursor()
        
        c.execute('SELECT COUNT(*) as count FROM questions WHERE status = ?', ('pending',))
        result = c.fetchone()
        
        return jsonify({'success': True, 'count': result['count']})
        
    except Exception as e:
        logger.error(f"Error getting questions count: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/questions/<int:question_id>/answer', methods=['POST', 'OPTIONS'])
@lecturer_required
def answer_question(question_id):
    """Lecturer answers a question."""
    if request.method == 'OPTIONS':
        return _build_cors_response()
    
    data = request.json
    answer = data.get('answer', '').strip()
    
    if not answer:
        return jsonify({'success': False, 'error': 'Answer required'}), 400
    
    try:
        with get_db() as conn:
            c = conn.cursor()
            
            c.execute('SELECT user_id, title FROM questions WHERE id = ?', (question_id,))
            question = c.fetchone()
            
            if not question:
                return jsonify({'success': False, 'error': 'Question not found'}), 404
            
            c.execute('''
                UPDATE questions 
                SET answer = ?, status = 'answered', answered_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (answer, question_id))
            
            conn.commit()
            
            create_notification(
                question['user_id'],
                'question_answer',
                'Question Answered',
                f'Lecturer answered: {question["title"]}',
                '/student.html?tab=questions'
            )
            
            return jsonify({'success': True})
            
    except Exception as e:
        logger.error(f"Error answering question: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

# ==================================================
# API ENDPOINTS - FEEDBACK
# ==================================================
@app.route('/api/feedback/enhanced', methods=['POST', 'OPTIONS'])
@login_required
def submit_enhanced_feedback():
    """Submit enhanced feedback."""
    if request.method == 'OPTIONS':
        return _build_cors_response()
    
    user_id = session['user_id']
    data = request.json
    
    subject = data.get('subject', '').strip()
    message = data.get('message', '').strip()
    session_id = data.get('session_id')
    
    if not subject or not message:
        return jsonify({'success': False, 'error': 'Subject and message required'}), 400
    
    try:
        with get_db() as conn:
            c = conn.cursor()
            c.execute('''
                INSERT INTO enhanced_feedback (user_id, session_id, subject, message, status)
                VALUES (?, ?, ?, ?, 'pending')
            ''', (user_id, session_id, subject, message))
            
            feedback_id = c.lastrowid
            conn.commit()
            
            # Notify lecturers
            c.execute('SELECT id FROM users WHERE role = "lecturer"')
            lecturers = c.fetchall()
            for lecturer in lecturers:
                create_notification(
                    lecturer['id'],
                    'feedback',
                    'New Feedback',
                    f'Student submitted feedback: {subject}',
                    '/lecturer.html?tab=feedback'
                )
            
            return jsonify({'success': True, 'feedback_id': feedback_id})
            
    except Exception as e:
        logger.error(f"Error submitting feedback: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/feedback/enhanced', methods=['GET', 'OPTIONS'])
@login_required
def get_enhanced_feedback():
    """Get feedback."""
    if request.method == 'OPTIONS':
        return _build_cors_response()
    
    user_id = session['user_id']
    role = session.get('role', 'student')
    
    try:
        with get_db() as conn:
            c = conn.cursor()
            
            if role == 'lecturer':
                c.execute('''
                    SELECT ef.*, u.username, u.full_name 
                    FROM enhanced_feedback ef
                    JOIN users u ON ef.user_id = u.id
                    ORDER BY 
                        CASE ef.status 
                            WHEN 'pending' THEN 1
                            WHEN 'answered' THEN 2
                            ELSE 3
                        END,
                        ef.created_at DESC
                ''')
            else:
                c.execute('''
                    SELECT ef.*, u.username, u.full_name 
                    FROM enhanced_feedback ef
                    JOIN users u ON ef.user_id = u.id
                    WHERE ef.user_id = ?
                    ORDER BY ef.created_at DESC
                ''', (user_id,))
            
            feedback = c.fetchall()
            
            result = []
            for fb in feedback:
                result.append({
                    'id': fb['id'],
                    'user_id': fb['user_id'],
                    'username': fb['username'],
                    'full_name': fb['full_name'],
                    'subject': fb['subject'],
                    'message': fb['message'],
                    'reply': fb['reply'],
                    'status': fb['status'],
                    'created_at': fb['created_at']
                })
            
            return jsonify({'success': True, 'feedback': result})
            
    except Exception as e:
        logger.error(f"Error getting feedback: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/feedback/count', methods=['GET', 'OPTIONS'])
@lecturer_required
def get_feedback_count():
    """Get count of pending feedback."""
    if request.method == 'OPTIONS':
        return _build_cors_response()
    
    try:
        conn = get_db()
        c = conn.cursor()
        
        c.execute('SELECT COUNT(*) as count FROM enhanced_feedback WHERE status = ?', ('pending',))
        result = c.fetchone()
        
        return jsonify({'success': True, 'count': result['count']})
        
    except Exception as e:
        logger.error(f"Error getting feedback count: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/feedback/enhanced/<int:feedback_id>/reply', methods=['POST', 'OPTIONS'])
@lecturer_required
def reply_to_feedback(feedback_id):
    """Lecturer replies to feedback."""
    if request.method == 'OPTIONS':
        return _build_cors_response()
    
    data = request.json
    reply = data.get('reply', '').strip()
    
    if not reply:
        return jsonify({'success': False, 'error': 'Reply required'}), 400
    
    try:
        with get_db() as conn:
            c = conn.cursor()
            
            c.execute('SELECT user_id, subject FROM enhanced_feedback WHERE id = ?', (feedback_id,))
            feedback = c.fetchone()
            
            if not feedback:
                return jsonify({'success': False, 'error': 'Feedback not found'}), 404
            
            c.execute('''
                UPDATE enhanced_feedback 
                SET reply = ?, status = 'answered', replied_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (reply, feedback_id))
            
            conn.commit()
            
            create_notification(
                feedback['user_id'],
                'feedback_reply',
                'Feedback Reply',
                f'Lecturer replied: {feedback["subject"]}',
                '/student.html?tab=feedback'
            )
            
            return jsonify({'success': True})
            
    except Exception as e:
        logger.error(f"Error replying to feedback: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

# ==================================================
# API ENDPOINTS - SUBMISSIONS
# ==================================================
@app.route('/api/submissions', methods=['POST', 'OPTIONS'])
@student_required
def record_submission():
    """Record student submission."""
    if request.method == 'OPTIONS':
        return _build_cors_response()
    
    user_id = session['user_id']
    data = request.json
    
    session_id = data.get('session_id')
    title = data.get('title', '')
    description = data.get('description', '')
    
    try:
        with get_db() as conn:
            c = conn.cursor()
            c.execute('''
                INSERT INTO submissions (user_id, session_id, title, description)
                VALUES (?, ?, ?, ?)
            ''', (user_id, session_id, title, description))
            
            submission_id = c.lastrowid
            conn.commit()
            
            return jsonify({'success': True, 'submission_id': submission_id})
            
    except Exception as e:
        logger.error(f"Error recording submission: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/submissions', methods=['GET', 'OPTIONS'])
@login_required
def get_submissions():
    """Get submissions."""
    if request.method == 'OPTIONS':
        return _build_cors_response()
    
    user_id = session['user_id']
    role = session.get('role', 'student')
    
    try:
        with get_db() as conn:
            c = conn.cursor()
            
            if role == 'lecturer':
                c.execute('''
                    SELECT s.*, u.username, u.full_name 
                    FROM submissions s
                    JOIN users u ON s.user_id = u.id
                    ORDER BY s.submitted_at DESC
                ''')
            else:
                c.execute('''
                    SELECT s.*, u.username, u.full_name 
                    FROM submissions s
                    JOIN users u ON s.user_id = u.id
                    WHERE s.user_id = ?
                    ORDER BY s.submitted_at DESC
                ''', (user_id,))
            
            submissions = c.fetchall()
            
            result = []
            for s in submissions:
                result.append({
                    'id': s['id'],
                    'user_id': s['user_id'],
                    'username': s['username'],
                    'full_name': s['full_name'],
                    'title': s['title'],
                    'description': s['description'],
                    'submitted_at': s['submitted_at'],
                    'session_id': s['session_id']
                })
            
            return jsonify({'success': True, 'submissions': result})
            
    except Exception as e:
        logger.error(f"Error getting submissions: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

# ==================================================
# COMPARISON VIEW ENDPOINTS
# ==================================================
@app.route('/api/compare/<int:session_id>/<path:file1>/<path:file2>', methods=['GET'])
@lecturer_required
def compare_files_lecturer(session_id, file1, file2):
    """Detailed comparison for lecturers with highlighting."""
    try:
        with get_db() as conn:
            c = conn.cursor()
            
            c.execute('SELECT * FROM uploaded_files WHERE session_id = ? AND filename = ?', 
                     (session_id, file1))
            f1 = c.fetchone()
            
            c.execute('SELECT * FROM uploaded_files WHERE session_id = ? AND filename = ?', 
                     (session_id, file2))
            f2 = c.fetchone()
            
            if not f1 or not f2:
                return "Files not found", 404
            
            file1_path = os.path.join(UPLOAD_FOLDER, f1['stored_filename'])
            file2_path = os.path.join(UPLOAD_FOLDER, f2['stored_filename'])
            
            text1 = load_text(file1_path)
            text2 = load_text(file2_path)
            
            highlighting = highlight_word_level(text1, text2)
            similarities = calculate_enhanced_similarity(text1, text2)
            
            # Get AI scores - FIXED: ensure they're not None
            ai_score1 = float(f1['ai_score']) if f1['ai_score'] is not None else 0
            ai_score2 = float(f2['ai_score']) if f2['ai_score'] is not None else 0
            
            # Generate HTML comparison page
            html = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <title>Plagiarism Comparison</title>
                <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Noto+Sans+Armenian:wght@400;500;600;700&display=swap" rel="stylesheet">
                <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
                <style>
                    * {{
                        margin: 0;
                        padding: 0;
                        box-sizing: border-box;
                    }}
                    
                    body {{
                        font-family: 'Inter', 'Noto Sans Armenian', sans-serif;
                        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                        min-height: 100vh;
                        padding: 20px;
                    }}
                    
                    .container {{
                        max-width: 1400px;
                        margin: 0 auto;
                    }}
                    
                    .header {{
                        background: white;
                        border-radius: 20px;
                        padding: 30px;
                        margin-bottom: 30px;
                        box-shadow: 0 4px 20px rgba(0,0,0,0.1);
                    }}
                    
                    h1 {{
                        background: linear-gradient(135deg, #667eea, #764ba2);
                        -webkit-background-clip: text;
                        background-clip: text;
                        color: transparent;
                        margin-bottom: 20px;
                    }}
                    
                    .stats {{
                        display: grid;
                        grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                        gap: 20px;
                    }}
                    
                    .stat-card {{
                        background: #f8f9ff;
                        padding: 20px;
                        border-radius: 15px;
                        text-align: center;
                    }}
                    
                    .stat-value {{
                        font-size: 2.5rem;
                        font-weight: 700;
                        color: #764ba2;
                    }}
                    
                    .stat-label {{
                        color: #666;
                        margin-top: 5px;
                    }}
                    
                    .comparison-grid {{
                        display: grid;
                        grid-template-columns: 1fr 1fr;
                        gap: 30px;
                    }}
                    
                    .file-column {{
                        background: white;
                        border-radius: 20px;
                        padding: 25px;
                        box-shadow: 0 4px 20px rgba(0,0,0,0.1);
                    }}
                    
                    .file-header {{
                        display: flex;
                        align-items: center;
                        gap: 15px;
                        padding: 15px;
                        background: linear-gradient(135deg, #667eea20, #764ba220);
                        border-radius: 12px;
                        margin-bottom: 20px;
                    }}
                    
                    .file-header i {{
                        font-size: 2rem;
                        color: #764ba2;
                    }}
                    
                    .file-name {{
                        font-weight: 600;
                        color: #333;
                        flex: 1;
                        word-break: break-word;
                    }}
                    
                    .ai-score {{
                        background: linear-gradient(135deg, #667eea, #764ba2);
                        color: white;
                        padding: 5px 15px;
                        border-radius: 25px;
                        font-size: 0.9rem;
                        white-space: nowrap;
                    }}
                    
                    .sentences-container {{
                        max-height: 500px;
                        overflow-y: auto;
                        padding-right: 10px;
                    }}
                    
                    .sentence {{
                        padding: 15px;
                        margin: 10px 0;
                        background: #f8f9ff;
                        border-radius: 10px;
                        border-left: 4px solid;
                    }}
                    
                    .sentence.plagiarized {{
                        border-left-color: #ff4757;
                    }}
                    
                    .word {{
                        display: inline-block;
                        padding: 2px 4px;
                        margin: 2px;
                        border-radius: 4px;
                        transition: all 0.2s ease;
                    }}
                    
                    .word.plagiarized {{
                        background: #ff4757;
                        color: white;
                        font-weight: 600;
                        padding: 2px 6px;
                        border-radius: 4px;
                    }}
                    
                    .legend {{
                        display: flex;
                        gap: 20px;
                        margin: 20px 0;
                        padding: 15px;
                        background: white;
                        border-radius: 12px;
                        flex-wrap: wrap;
                    }}
                    
                    .legend-item {{
                        display: flex;
                        align-items: center;
                        gap: 8px;
                    }}
                    
                    .legend-color {{
                        width: 20px;
                        height: 20px;
                        border-radius: 4px;
                    }}
                    
                    .back-btn {{
                        display: inline-flex;
                        align-items: center;
                        gap: 10px;
                        padding: 12px 25px;
                        background: white;
                        color: #764ba2;
                        text-decoration: none;
                        border-radius: 10px;
                        font-weight: 500;
                        border: 2px solid #764ba2;
                        transition: all 0.3s ease;
                        margin-bottom: 20px;
                    }}
                    
                    .back-btn:hover {{
                        background: linear-gradient(135deg, #667eea, #764ba2);
                        color: white;
                        transform: translateY(-2px);
                    }}
                    
                    @media (max-width: 768px) {{
                        .comparison-grid {{
                            grid-template-columns: 1fr;
                        }}
                        
                        .stats {{
                            grid-template-columns: 1fr;
                        }}
                    }}
                </style>
            </head>
            <body>
                <div class="container">
                    <a href="/lecturer.html" class="back-btn">
                        <i class="fas fa-arrow-left"></i> Back to Dashboard
                    </a>
                    
                    <div class="header">
                        <h1>Detailed Plagiarism Analysis</h1>
                        <div class="stats">
                            <div class="stat-card">
                                <div class="stat-value">{similarities['combined_similarity']}%</div>
                                <div class="stat-label">Overall Similarity</div>
                            </div>
                            <div class="stat-card">
                                <div class="stat-value">{similarities['basic_similarity']}%</div>
                                <div class="stat-label">Word Overlap</div>
                            </div>
                            <div class="stat-card">
                                <div class="stat-value">{similarities['semantic_similarity']}%</div>
                                <div class="stat-label">Semantic</div>
                            </div>
                        </div>
                        
                        <div class="legend">
                            <div class="legend-item">
                                <div class="legend-color" style="background: #ff4757;"></div>
                                <span>Plagiarized words (red)</span>
                            </div>
                            <div class="legend-item">
                                <div class="legend-color" style="background: transparent; border: 1px solid #ccc;"></div>
                                <span>Original text</span>
                            </div>
                        </div>
                    </div>
                    
                    <div class="comparison-grid">
                        <div class="file-column">
                            <div class="file-header">
                                <i class="fas fa-file-alt"></i>
                                <span class="file-name">{file1}</span>
                                <span class="ai-score">AI: {ai_score1:.1f}%</span>
                            </div>
                            <div class="sentences-container">
            """
            
            # Add sentences for file1 with RED highlighting for plagiarized words
            for sent in highlighting.get('file1', []):
                sent_class = 'sentence plagiarized' if sent.get('plagiarized') else 'sentence'
                html += f'<div class="{sent_class}">'
                for word in sent.get('words', []):
                    if word.get('plagiarized'):
                        html += f'<span class="word plagiarized" style="background-color: #ff4757; color: white; font-weight: bold; padding: 2px 6px; border-radius: 4px;">{word["text"]}</span> '
                    else:
                        html += f'<span class="word">{word["text"]}</span> '
                if sent.get('similarity', 0) > 0:
                    html += f'<br><small style="color: #666; margin-top: 5px;">Similarity: {sent["similarity"]}%</small>'
                html += '</div>'
            
            html += f"""
                            </div>
                        </div>
                        
                        <div class="file-column">
                            <div class="file-header">
                                <i class="fas fa-file-alt"></i>
                                <span class="file-name">{file2}</span>
                                <span class="ai-score">AI: {ai_score2:.1f}%</span>
                            </div>
                            <div class="sentences-container">
            """
            
            # Add sentences for file2 with RED highlighting for plagiarized words
            for sent in highlighting.get('file2', []):
                sent_class = 'sentence plagiarized' if sent.get('plagiarized') else 'sentence'
                html += f'<div class="{sent_class}">'
                for word in sent.get('words', []):
                    if word.get('plagiarized'):
                        html += f'<span class="word plagiarized" style="background-color: #ff4757; color: white; font-weight: bold; padding: 2px 6px; border-radius: 4px;">{word["text"]}</span> '
                    else:
                        html += f'<span class="word">{word["text"]}</span> '
                if sent.get('similarity', 0) > 0:
                    html += f'<br><small style="color: #666; margin-top: 5px;">Similarity: {sent["similarity"]}%</small>'
                html += '</div>'
            
            html += """
                            </div>
                        </div>
                    </div>
                </div>
            </body>
            </html>
            """
            
            return html
            
    except Exception as e:
        logger.error(f"Error generating comparison: {e}")
        import traceback
        traceback.print_exc()
        return f"Error: {str(e)}", 500

@app.route('/api/compare-student/<int:session_id>/<path:file1>/<path:file2>', methods=['GET'])
@student_required
def compare_files_student(session_id, file1, file2):
    """Summary view for students."""
    try:
        with get_db() as conn:
            c = conn.cursor()
            
            c.execute('SELECT * FROM uploaded_files WHERE session_id = ? AND filename = ?', 
                     (session_id, file1))
            f1 = c.fetchone()
            
            c.execute('SELECT * FROM uploaded_files WHERE session_id = ? AND filename = ?', 
                     (session_id, file2))
            f2 = c.fetchone()
            
            if not f1 or not f2:
                return "Files not found", 404
            
            file1_path = os.path.join(UPLOAD_FOLDER, f1['stored_filename'])
            file2_path = os.path.join(UPLOAD_FOLDER, f2['stored_filename'])
            
            text1 = load_text(file1_path)
            text2 = load_text(file2_path)
            
            similarities = calculate_enhanced_similarity(text1, text2)
            
            # Get AI scores - FIXED: ensure they're not None
            ai_score1 = float(f1['ai_score']) if f1['ai_score'] is not None else 0
            ai_score2 = float(f2['ai_score']) if f2['ai_score'] is not None else 0
            
            # Generate HTML
            html = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <title>Plagiarism Summary</title>
                <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Noto+Sans+Armenian:wght@400;500;600;700&display=swap" rel="stylesheet">
                <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
                <style>
                    * {{
                        margin: 0;
                        padding: 0;
                        box-sizing: border-box;
                    }}
                    
                    body {{
                        font-family: 'Inter', 'Noto Sans Armenian', sans-serif;
                        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                        min-height: 100vh;
                        padding: 20px;
                    }}
                    
                    .container {{
                        max-width: 1000px;
                        margin: 0 auto;
                    }}
                    
                    .header {{
                        background: white;
                        border-radius: 20px;
                        padding: 30px;
                        margin-bottom: 30px;
                        box-shadow: 0 4px 20px rgba(0,0,0,0.1);
                    }}
                    
                    h1 {{
                        background: linear-gradient(135deg, #667eea, #764ba2);
                        -webkit-background-clip: text;
                        background-clip: text;
                        color: transparent;
                        margin-bottom: 20px;
                    }}
                    
                    .summary-card {{
                        background: white;
                        border-radius: 20px;
                        padding: 30px;
                        margin-bottom: 20px;
                        box-shadow: 0 4px 20px rgba(0,0,0,0.1);
                    }}
                    
                    .file-names {{
                        display: flex;
                        align-items: center;
                        justify-content: center;
                        gap: 20px;
                        margin-bottom: 30px;
                        font-size: 18px;
                        flex-wrap: wrap;
                    }}
                    
                    .similarity-meter {{
                        height: 30px;
                        background: #e2e8f0;
                        border-radius: 15px;
                        margin: 20px 0;
                        overflow: hidden;
                    }}
                    
                    .similarity-fill {{
                        height: 100%;
                        background: linear-gradient(90deg, #667eea, #764ba2);
                        border-radius: 15px;
                        transition: width 0.5s ease;
                    }}
                    
                    .stats-grid {{
                        display: grid;
                        grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                        gap: 20px;
                        margin: 30px 0;
                    }}
                    
                    .stat-box {{
                        background: #f8f9ff;
                        padding: 20px;
                        border-radius: 10px;
                        text-align: center;
                    }}
                    
                    .stat-label {{
                        color: #666;
                        margin-bottom: 10px;
                    }}
                    
                    .stat-value {{
                        font-size: 32px;
                        font-weight: bold;
                        color: #764ba2;
                    }}
                    
                    .back-btn {{
                        display: inline-flex;
                        align-items: center;
                        gap: 10px;
                        padding: 12px 25px;
                        background: white;
                        color: #764ba2;
                        text-decoration: none;
                        border-radius: 10px;
                        font-weight: 500;
                        border: 2px solid #764ba2;
                        transition: all 0.3s ease;
                        margin-bottom: 20px;
                    }}
                    
                    .back-btn:hover {{
                        background: linear-gradient(135deg, #667eea, #764ba2);
                        color: white;
                        transform: translateY(-2px);
                    }}
                </style>
            </head>
            <body>
                <div class="container">
                    <a href="/student.html" class="back-btn">
                        <i class="fas fa-arrow-left"></i> Back to Dashboard
                    </a>
                    
                    <div class="header">
                        <h1><i class="fas fa-chart-bar"></i> Plagiarism Analysis Summary</h1>
                    </div>
                    
                    <div class="summary-card">
                        <div class="file-names">
                            <span><i class="fas fa-file-alt"></i> {file1}</span>
                            <i class="fas fa-exchange-alt"></i>
                            <span><i class="fas fa-file-alt"></i> {file2}</span>
                        </div>
                        
                        <div class="similarity-meter">
                            <div class="similarity-fill" style="width: {similarities['combined_similarity']}%;"></div>
                        </div>
                        
                        <div class="stats-grid">
                            <div class="stat-box">
                                <div class="stat-label">Overall Similarity</div>
                                <div class="stat-value">{similarities['combined_similarity']}%</div>
                            </div>
                            <div class="stat-box">
                                <div class="stat-label">Word Overlap</div>
                                <div class="stat-value">{similarities['basic_similarity']}%</div>
                            </div>
                            <div class="stat-box">
                                <div class="stat-label">Semantic</div>
                                <div class="stat-value">{similarities['semantic_similarity']}%</div>
                            </div>
                        </div>
                        
                        <h3 style="margin-top: 30px;"><i class="fas fa-robot"></i> AI Content Detection</h3>
                        
                        <div class="stats-grid">
                            <div class="stat-box">
                                <div class="stat-label">{file1}</div>
                                <div class="stat-value">{ai_score1:.1f}%</div>
                                <div style="margin-top: 10px;">
                                    {'⚠️ AI Generated' if ai_score1 > 55 else '✅ Human Written'}
                                </div>
                            </div>
                            <div class="stat-box">
                                <div class="stat-label">{file2}</div>
                                <div class="stat-value">{ai_score2:.1f}%</div>
                                <div style="margin-top: 10px;">
                                    {'⚠️ AI Generated' if ai_score2 > 55 else '✅ Human Written'}
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </body>
            </html>
            """
            
            return html
            
    except Exception as e:
        logger.error(f"Error generating student summary: {e}")
        return f"Error: {str(e)}", 500

# ==================================================
# TEST HIGHLIGHT ENDPOINT - ADD THIS!
# ==================================================
@app.route('/api/test-highlight', methods=['POST', 'OPTIONS'])
@login_required
def test_highlight():
    """Test highlighting with two text inputs"""
    if request.method == 'OPTIONS':
        return _build_cors_response()
    
    data = request.json
    text1 = data.get('text1', '')
    text2 = data.get('text2', '')
    
    if not text1 or not text2:
        return jsonify({'error': 'Both texts required'}), 400
    
    highlighting = highlight_word_level(text1, text2)
    similarities = calculate_enhanced_similarity(text1, text2)
    
    return jsonify({
        'success': True,
        'similarities': similarities,
        'highlighting': highlighting
    })

# ==================================================
# TEST ENDPOINT
# ==================================================
@app.route('/api/test', methods=['GET', 'OPTIONS'])
def test():
    if request.method == 'OPTIONS':
        return _build_cors_response()
    
    return jsonify({
        'success': True,
        'message': 'Server is running!',
        'time': str(datetime.now()),
        'features': {
            'semantic_model': MODEL_AVAILABLE,
            'synonyms_loaded': bool(SYNONYMS),
            'themes_loaded': bool(THEME_KEYWORDS),
            'stopwords_loaded': bool(STOPWORDS)
        }
    })

# ==================================================
# CORS HELPER
# ==================================================
def _build_cors_response():
    response = make_response()
    response.headers.add('Access-Control-Allow-Origin', 'http://127.0.0.1:5000')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type, Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS')
    response.headers.add('Access-Control-Allow-Credentials', 'true')
    return response

# ==================================================
# STATIC FILE SERVING
# ==================================================
@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

@app.route('/<path:path>')
def serve_file(path):
    return send_from_directory('.', path)

@app.route('/lecturer.html')
def lecturer_page():
    return send_from_directory('.', 'lecturer.html')

@app.route('/student.html')
def student_page():
    return send_from_directory('.', 'student.html')

# ==================================================
# MAIN
# ==================================================
if __name__ == '__main__':
    print("=" * 70)
    print("🚀 ARMENIAN PLAGIARISM DETECTION SYSTEM - COMPLETE FIXED VERSION")
    print("=" * 70)
    print("📚 Bachelor's Thesis - Information Security")
    print("👩‍🎓 Lilit Khalafyan")
    print("🏛️  National Polytechnic University")
    print("=" * 70)

    # Initialize database
    init_db()

    # Create test users if they don't exist
    try:
        with get_db() as conn:
            c = conn.cursor()
            
            # Create test lecturer
            c.execute("SELECT * FROM users WHERE username = 'lecturer'")
            if not c.fetchone():
                password_hash, salt = hash_password('lecturer123')
                c.execute('''
                    INSERT INTO users (username, full_name, email, password_hash, salt, role)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', ('lecturer', 'Test Lecturer', 'lecturer@example.com', 
                      password_hash, salt, 'lecturer'))
                print("✅ Created test lecturer: username='lecturer', password='lecturer123'")
            else:
                print("✅ Test lecturer already exists")
            
            # Create test student
            c.execute("SELECT * FROM users WHERE username = 'student'")
            if not c.fetchone():
                password_hash, salt = hash_password('student123')
                c.execute('''
                    INSERT INTO users (username, full_name, email, password_hash, salt, role)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', ('student', 'Test Student', 'student@example.com', 
                      password_hash, salt, 'student'))
                print("✅ Created test student: username='student', password='student123'")
            else:
                print("✅ Test student already exists")
            
            conn.commit()
            
            # List all users
            c.execute("SELECT username, role FROM users")
            users = c.fetchall()
            print(f"📊 Users in database: {len(users)}")
            for user in users:
                print(f"   - {user['username']} ({user['role']})")
                
    except Exception as e:
        logger.error(f"Error creating test users: {e}")

    print("=" * 70)
    print("📁 Upload folder: uploads/")
    print("🌐 Server URL: http://localhost:5000")
    print("👥 Lecturer: username='lecturer', password='lecturer123'")
    print("👥 Student: username='student', password='student123'")
    print("📝 Log file: plagiarism_detector.log")
    print("=" * 70)
    
    # Run the app
    app.run(debug=True, port=5000, host='0.0.0.0')