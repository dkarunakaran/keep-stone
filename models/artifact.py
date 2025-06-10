from sqlalchemy import Column, Integer, String, ForeignKey, Date, DateTime, Text, JSON, Boolean
from .base import Base
from datetime import datetime, date, timedelta

class Artifact(Base):
    __tablename__ = 'artifact'
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    images = Column(JSON, default=list)  # Will store list of {name: filename, path: relative_path}
    type_id = Column(Integer, ForeignKey('type.id'))
    expiry_date = Column(Date, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow())
    last_notification_sent = Column(DateTime, nullable=True)
    notification_count = Column(Integer, default=0)
    deleted = Column(Boolean, default=False)
    deleted_at = Column(DateTime, nullable=True)


    def is_expired(self):
        expiry_date = None
        if self.expiry_date is not None:
            expiry_date = self.expiry_date < date.today()
        return expiry_date
    
    def can_send_notification(self, config):
        """Check if we can send another notification"""
        if not self.expiry_date or not self.is_token():
            return False

        # Get config values
        hours_between_notifications = config['email'].get('notification_interval', 24)  # Fixed gap
        notification_days = config['email'].get('notification_days', 14)
        max_notifications = config['email'].get('max_notifications', 3)

        # Check if we've hit the notification limit
        if self.notification_count >= max_notifications:
            return False

        # Check if token is within notification window
        days_until_expiry = (self.expiry_date - date.today()).days
        if days_until_expiry > notification_days or days_until_expiry < 0:
            return False

        # Check if 24 hours have passed since last notification
        if self.last_notification_sent:
            hours_since_last = (datetime.utcnow() - self.last_notification_sent).total_seconds() / 3600
            if hours_since_last < hours_between_notifications:
                return False

        return True
    
    def record_notification(self):
        """Update notification tracking"""
        self.notification_count += 1
        self.last_notification_sent = datetime.utcnow()

    def is_token(self):
        """Check if artifact is a token"""
        return self.type_id == 1  # Assuming 1 is Token type_id
    
    def soft_delete(self):
        """Soft delete the artifact"""
        self.deleted = True
        self.deleted_at = datetime.utcnow()

    def is_ready_for_cleanup(self, config):
        """Check if artifact is ready for permanent deletion"""
        if not self.deleted or not self.deleted_at:
            return False
        cleanup_threshold = datetime.utcnow() - timedelta(hours=config['storage'].get('cleanup_threshold_hours', 24))
        return self.deleted_at <= cleanup_threshold