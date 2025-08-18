from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
import json
from .base import Base


class ProjectConfig(Base):
    """Model for project-specific configuration settings"""
    __tablename__ = 'project_config'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(Integer, ForeignKey('project.id'), nullable=False)
    key = Column(String, nullable=False)  # Configuration key (e.g., 'type', 'default_type')
    value = Column(Text, nullable=False)  # JSON-encoded value
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationship to project
    project = relationship("Project", back_populates="configs")
    
    def get_parsed_value(self):
        """Get the value parsed from JSON"""
        try:
            return json.loads(self.value)
        except (json.JSONDecodeError, TypeError):
            return self.value
    
    def set_value(self, value):
        """Set the value as JSON"""
        if isinstance(value, (list, dict)):
            self.value = json.dumps(value)
        else:
            self.value = str(value)
        self.updated_at = datetime.utcnow()
