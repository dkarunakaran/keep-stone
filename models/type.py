from sqlalchemy import Column, Integer, String
from .base import Base

class Type(Base):
    __tablename__ = 'type'
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String)