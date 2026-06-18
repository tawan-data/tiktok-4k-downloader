from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from extensions import db
from models import User
import re

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

def validate_email(email):
    """Validate email format"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email)

def validate_username(username):
    """Validate username"""
    pattern = r'^[a-zA-Z0-9_]{3,20}$'
    return re.match(pattern, username)

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    """User Registration"""
    if request.method == 'GET':
        return render_template('register.html')
    
    try:
        data = request.get_json() or request.form
        
        username = data.get('username', '').strip()
        email = data.get('email', '').strip()
        password = data.get('password', '')
        confirm_password = data.get('confirm_password', '')
        
        # Validation
        if not all([username, email, password]):
            return jsonify({'error': 'All fields are required'}), 400
        
        if not validate_username(username):
            return jsonify({'error': 'Username must be 3-20 characters (letters, numbers, underscore)'}), 400
        
        if not validate_email(email):
            return jsonify({'error': 'Invalid email format'}), 400
        
        if len(password) < 8:
            return jsonify({'error': 'Password must be at least 8 characters'}), 400
        
        if password != confirm_password:
            return jsonify({'error': 'Passwords do not match'}), 400
        
        # Check existing user
        if User.query.filter_by(username=username).first():
            return jsonify({'error': 'Username already exists'}), 400
        
        if User.query.filter_by(email=email).first():
            return jsonify({'error': 'Email already registered'}), 400
        
        # Create user
        user = User(username=username, email=email)
        user.set_password(password)
        
        db.session.add(user)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Registration successful! Please login.',
            'redirect': url_for('auth.login')
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """User Login"""
    if request.method == 'GET':
        return render_template('login.html')
    
    try:
        data = request.get_json() or request.form
        
        username = data.get('username', '').strip()
        password = data.get('password', '')
        remember = data.get('remember', False)
        
        if not username or not password:
            return jsonify({'error': 'Username and password are required'}), 400
        
        # Find user
        user = User.query.filter(
            (User.username == username) | (User.email == username)
        ).first()
        
        if not user or not user.check_password(password):
            return jsonify({'error': 'Invalid username or password'}), 401
        
        if not user.is_active:
            return jsonify({'error': 'Account is deactivated'}), 403
        
        # Login
        login_user(user, remember=remember)
        user.last_login = datetime.utcnow()
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Login successful!',
            'redirect': url_for('dashboard.index'),
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email
            }
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@auth_bp.route('/logout')
@login_required
def logout():
    """User Logout"""
    logout_user()
    return jsonify({
        'success': True,
        'message': 'Logged out successfully',
        'redirect': url_for('index')
    }), 200


@auth_bp.route('/profile', methods=['GET', 'PUT'])
@login_required
def profile():
    """Get or Update User Profile"""
    if request.method == 'GET':
        return jsonify({
            'user': {
                'id': current_user.id,
                'username': current_user.username,
                'email': current_user.email,
                'full_name': current_user.full_name,
                'avatar': current_user.avatar,
                'total_downloads': current_user.total_downloads,
                'settings': current_user.settings,
                'created_at': current_user.created_at.isoformat()
            }
        }), 200
    
    # PUT - Update profile
    try:
        data = request.get_json()
        
        if 'full_name' in data:
            current_user.full_name = data['full_name']
        
        if 'avatar' in data:
            current_user.avatar = data['avatar']
        
        if 'settings' in data:
            current_user.settings.update(data['settings'])
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Profile updated successfully',
            'user': {
                'id': current_user.id,
                'username': current_user.username,
                'email': current_user.email,
                'full_name': current_user.full_name,
                'avatar': current_user.avatar,
                'settings': current_user.settings
            }
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@auth_bp.route('/change-password', methods=['POST'])
@login_required
def change_password():
    """Change Password"""
    try:
        data = request.get_json()
        
        old_password = data.get('old_password')
        new_password = data.get('new_password')
        confirm_password = data.get('confirm_password')
        
        if not all([old_password, new_password, confirm_password]):
            return jsonify({'error': 'All fields are required'}), 400
        
        if not current_user.check_password(old_password):
            return jsonify({'error': 'Current password is incorrect'}), 401
        
        if len(new_password) < 8:
            return jsonify({'error': 'New password must be at least 8 characters'}), 400
        
        if new_password != confirm_password:
            return jsonify({'error': 'Passwords do not match'}), 400
        
        current_user.set_password(new_password)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Password changed successfully'
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500
