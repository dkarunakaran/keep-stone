"""API Key model for REST API authentication"""
import secrets
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, ForeignKey
from sqlalchemy.orm import relationship
from models.base import Base


class ApiKey(Base):
    """API Key for programmatic access to KeepStone"""
    __tablename__ = 'api_keys'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    key_hash = Column(String(64), unique=True, nullable=False, index=True)
    name = Column(String(100), nullable=False)
    prefix = Column(String(8), nullable=False)  # First 8 chars for display
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    last_used_at = Column(DateTime)
    expires_at = Column(DateTime)
    permissions = Column(Text, default='read')  # 'read', 'write', 'admin'

    # Relationship
    user = relationship("User", backref="api_keys")

    @staticmethod
    def generate_key():
        """Generate a new API key with prefix for identification"""
        # Generate a 32-byte random key (64 hex chars)
        key = secrets.token_hex(32)
        return key

    @staticmethod
    def hash_key(key):
        """Hash the API key for storage"""
        import hashlib
        return hashlib.sha256(key.encode()).hexdigest()

    @classmethod
    def get_by_raw_key(cls, session, raw_key):
        """Find API key by raw key value"""
        key_hash = cls.hash_key(raw_key)
        return session.query(cls).filter_by(key_hash=key_hash).first()

    @classmethod
    def create(cls, user_id, name, permissions='read', expires_at=None):
        """Create a new API key"""
        raw_key = cls.generate_key()
        key_hash = cls.hash_key(raw_key)
        prefix = raw_key[:8]

        api_key = cls(
            user_id=user_id,
            key_hash=key_hash,
            name=name,
            prefix=prefix,
            permissions=permissions,
            expires_at=expires_at
        )
        return api_key, raw_key  # Return both object and raw key (only shown once)

    def verify(self, raw_key):
        """Verify if the provided key matches"""
        return self.key_hash == self.hash_key(raw_key)

    def is_valid(self):
        """Check if key is active and not expired"""
        if not self.is_active:
            return False
        if self.expires_at and datetime.utcnow() > self.expires_at:
            return False
        return True

    def has_permission(self, required):
        """Check if key has required permission level"""
        levels = {'read': 1, 'write': 2, 'admin': 3}
        return levels.get(self.permissions, 0) >= levels.get(required, 0)

    def update_last_used(self):
        """Update the last used timestamp"""
        self.last_used_at = datetime.utcnow()

    def to_dict(self, include_key=False):
        """Convert to dictionary"""
        result = {
            'id': self.id,
            'name': self.name,
            'prefix': self.prefix,
            'is_active': self.is_active,
            'permissions': self.permissions,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'last_used_at': self.last_used_at.isoformat() if self.last_used_at else None,
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
        }
        if include_key:
            result['key'] = self.key_hash
        return result
