from sqlalchemy import Column, Integer, String, ForeignKey, Date, DateTime, Text, JSON
from .base import Base
from datetime import datetime, date

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
        notify_threshold = config['email'].get('notify_threshold', 24)  # hours
        notification_days = config['email'].get('notification_days', 14)
        max_notifications = config['email'].get('max_notifications', 3)

        # Check if we've hit the notification limit
        if self.notification_count >= max_notifications:
            return False

        # Check if token is within notification window
        days_until_expiry = (self.expiry_date - date.today()).days
        if days_until_expiry > notification_days or days_until_expiry < 0:
            return False

        # Check if enough time has passed since last notification
        if self.last_notification_sent:
            hours_since_last = (datetime.utcnow() - self.last_notification_sent).total_seconds() / 3600
            if hours_since_last < notify_threshold:
                return False

        return True
    
    def record_notification(self):
        """Update notification tracking"""
        self.notification_count += 1
        self.last_notification_sent = datetime.utcnow()

    def is_token(self):
        """Check if artifact is a token"""
        return self.type_id == 1  # Assuming 1 is Token type_id