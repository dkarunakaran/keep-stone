from sqlalchemy import Column, Integer, String, ForeignKey, Date, DateTime, Text, JSON
from .base import Base
from datetime import datetime, date

class Artifact(Base):
    __tablename__ = 'artifact'
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    images = Column(JSON, nullable=True)  # Store array of image objects
    type_id = Column(Integer, ForeignKey('type.id'))
    expiry_date = Column(Date, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow())

    def is_expired(self):
        return self.expiry_date < date.today()