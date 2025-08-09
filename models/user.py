from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from datetime import datetime
from models.base import Base

class User(UserMixin, Base):
    """User model for authentication and authorization"""
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True)
    username = Column(String(80), unique=True, nullable=False, index=True)
    email = Column(String(120), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(100), nullable=False)
    is_admin = Column(Boolean, default=False, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login = Column(DateTime)
    notes = Column(Text)
    
    def __init__(self, username, email, password, full_name, is_admin=False, is_active=True, notes=None):
        self.username = username
        self.email = email
        self.set_password(password)
        self.full_name = full_name
        self.is_admin = is_admin
        self.is_active = is_active
        self.notes = notes
    
    def set_password(self, password):
        """Hash and set the user password"""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        """Check if provided password matches the hashed password"""
        return check_password_hash(self.password_hash, password)
    
    def update_last_login(self):
        """Update the last login timestamp"""
        self.last_login = datetime.utcnow()
    
    def get_id(self):
        """Return the user ID as a string (required by Flask-Login)"""
        return str(self.id)
    
    def is_authenticated(self):
        """Return True if the user is authenticated"""
        return True
    
    def is_anonymous(self):
        """Return False as this is not an anonymous user"""
        return False
    
    def __repr__(self):
        return f'<User {self.username}>'
    
    def to_dict(self):
        """Convert user object to dictionary for JSON serialization"""
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'full_name': self.full_name,
            'is_admin': self.is_admin,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'last_login': self.last_login.isoformat() if self.last_login else None,
            'notes': self.notes
        }
    
    @classmethod
    def create_admin_user(cls, username="admin", email="admin@keepstone.local", 
                         password="admin123", full_name="Administrator"):
        """Create a default admin user"""
        return cls(
            username=username,
            email=email,
            password=password,
            full_name=full_name,
            is_admin=True,
            is_active=True,
            notes="Default administrator account"
        )
    
    @staticmethod
    def validate_username(username):
        """Validate username format"""
        if not username or len(username) < 3 or len(username) > 80:
            return False, "Username must be between 3 and 80 characters"
        if not username.replace('_', '').replace('-', '').isalnum():
            return False, "Username can only contain letters, numbers, hyphens, and underscores"
        return True, ""
    
    @staticmethod
    def validate_email(email):
        """Basic email validation"""
        import re
        if not email or len(email) > 120:
            return False, "Email is required and must be less than 120 characters"
        
        email_regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_regex, email):
            return False, "Invalid email format"
        return True, ""
    
    @staticmethod
    def validate_password(password):
        """Validate password strength"""
        if not password or len(password) < 6:
            return False, "Password must be at least 6 characters long"
        if len(password) > 255:
            return False, "Password must be less than 255 characters"
        return True, ""
