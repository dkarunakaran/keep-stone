from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text
from .base import Base
from datetime import datetime

class Project(Base):
    __tablename__ = 'project'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False, unique=True)
    description = Column(Text, nullable=True)
    is_default = Column(Boolean, default=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<Project {self.name}>'
    
    def set_as_default(self, session):
        """Set this project as default and unset all others"""
        # First, unset all other projects as default
        session.query(Project).update({Project.is_default: False})
        # Then set this one as default
        self.is_default = True
        session.commit()
