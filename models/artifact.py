from sqlalchemy import Column, Integer, String, ForeignKey, Date, DateTime
from .base import Base
from datetime import datetime, date

class Artifact(Base):
    __tablename__ = 'artifact'
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)
    used_for = Column(String, nullable=False)
    type_id = Column(Integer, ForeignKey('type.id'))
    expiry_date = Column(Date, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow())

    def is_expired(self):
        return self.expiry_date < date.today()