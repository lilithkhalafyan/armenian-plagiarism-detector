"""
Authentication utilities for Armenian Plagiarism Detection System
"""

import hashlib
import os
from functools import wraps
from flask import session, jsonify


def hash_password(password):
    """Hash a password with a random salt"""
    salt = os.urandom(32)
    password_hash = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, 100000)
    return password_hash.hex(), salt.hex()


def verify_password(password, password_hash, salt):
    """Verify a password against its hash and salt"""
    try:
        salt_bytes = bytes.fromhex(salt)
        password_hash_bytes = bytes.fromhex(password_hash)
        test_hash = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt_bytes, 100000)
        return test_hash == password_hash_bytes
    except (ValueError, TypeError):
        return False


def login_required(f):
    """Decorator to require user login"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'success': False, 'error': 'Authentication required'}), 401
        return f(*args, **kwargs)
    return decorated_function


def lecturer_required(f):
    """Decorator to require lecturer role"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'success': False, 'error': 'Authentication required'}), 401
        if session.get('role') != 'lecturer':
            return jsonify({'success': False, 'error': 'Lecturer access required'}), 403
        return f(*args, **kwargs)
    return decorated_function


def student_required(f):
    """Decorator to require student role"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'success': False, 'error': 'Authentication required'}), 401
        if session.get('role') != 'student':
            return jsonify({'success': False, 'error': 'Student access required'}), 403
        return f(*args, **kwargs)
    return decorated_function