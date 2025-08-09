"""
Authentication utilities for KeepStone application
"""

from functools import wraps
from flask import redirect, url_for, flash, request, session
from flask_login import current_user

def login_required(f):
    """Decorator to require user authentication"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    """Decorator to require admin privileges"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('login', next=request.url))
        
        if not current_user.is_admin:
            flash('Admin privileges required to access this page.', 'error')
            return redirect(url_for('index'))
        
        return f(*args, **kwargs)
    return decorated_function

def active_user_required(f):
    """Decorator to require active user status"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('login', next=request.url))
        
        if not current_user.is_active:
            flash('Your account has been deactivated. Please contact an administrator.', 'error')
            return redirect(url_for('logout'))
        
        return f(*args, **kwargs)
    return decorated_function

def get_safe_redirect_url(next_url=None):
    """Get a safe redirect URL, preventing open redirects"""
    if next_url:
        # Only allow relative URLs to prevent open redirects
        if next_url.startswith('/') and not next_url.startswith('//'):
            return next_url
    return url_for('index')

def init_default_admin(session, User):
    """Initialize default admin user if no users exist"""
    try:
        # Check if any users exist
        user_count = session.query(User).count()
        
        if user_count == 0:
            # Create default admin user
            admin_user = User.create_admin_user()
            session.add(admin_user)
            session.commit()
            print("Default admin user created:")
            print(f"  Username: {admin_user.username}")
            print(f"  Email: {admin_user.email}")
            print(f"  Password: admin123")
            print("  Please change the default password after first login!")
            return admin_user
        
        return None
    except Exception as e:
        print(f"Error creating default admin user: {e}")
        session.rollback()
        return None

def validate_user_data(username, email, password, full_name, is_editing=False):
    """Validate user input data"""
    errors = []
    
    # Validate username
    valid, message = User.validate_username(username) if 'User' in globals() else (True, "")
    if not valid:
        errors.append(message)
    
    # Validate email
    valid, message = User.validate_email(email) if 'User' in globals() else (True, "")
    if not valid:
        errors.append(message)
    
    # Validate password (only if not editing or if password is provided)
    if not is_editing or password:
        valid, message = User.validate_password(password) if 'User' in globals() else (True, "")
        if not valid:
            errors.append(message)
    
    # Validate full name
    if not full_name or len(full_name.strip()) < 2:
        errors.append("Full name must be at least 2 characters long")
    if len(full_name) > 100:
        errors.append("Full name must be less than 100 characters")
    
    return errors

def check_unique_user_fields(session, User, username, email, exclude_user_id=None):
    """Check if username and email are unique"""
    errors = []
    
    # Check username uniqueness
    username_query = session.query(User).filter(User.username == username)
    if exclude_user_id:
        username_query = username_query.filter(User.id != exclude_user_id)
    
    if username_query.first():
        errors.append("Username already exists")
    
    # Check email uniqueness
    email_query = session.query(User).filter(User.email == email)
    if exclude_user_id:
        email_query = email_query.filter(User.id != exclude_user_id)
    
    if email_query.first():
        errors.append("Email already exists")
    
    return errors

def format_user_for_display(user):
    """Format user data for safe display in templates"""
    return {
        'id': user.id,
        'username': user.username,
        'email': user.email,
        'full_name': user.full_name,
        'is_admin': user.is_admin,
        'is_active': user.is_active,
        'created_at': user.created_at.strftime('%Y-%m-%d %H:%M') if user.created_at else 'Unknown',
        'last_login': user.last_login.strftime('%Y-%m-%d %H:%M') if user.last_login else 'Never',
        'notes': user.notes or ''
    }

def log_user_activity(user, activity, details=None):
    """Log user activity (placeholder for future audit trail)"""
    # This could be expanded to log to a database table or file
    print(f"User Activity - {user.username}: {activity}")
    if details:
        print(f"  Details: {details}")

# Import User model at the end to avoid circular imports
try:
    from models.user import User
except ImportError:
    User = None
