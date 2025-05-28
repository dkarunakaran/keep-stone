from sqlalchemy import Column, Integer, String, ForeignKey, Date, DateTime
from .base import Base
import datetime

class Artifact(Base):
    __tablename__ = 'artifact'
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)
    used_for = Column(String, nullable=False)
    type_id = Column(Integer, ForeignKey('type.id'))
    expiry_date = Column(Date, nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.datetime.utcnow())