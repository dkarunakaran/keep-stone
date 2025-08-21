from sqlalchemy import Column, Integer, String, Boolean, Text
from .base import Base

class Tool(Base):
    __tablename__ = 'tools'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(100), unique=True, nullable=False)  # e.g., 'json_to_csv'
    display_name = Column(String(200), nullable=False)       # e.g., 'JSON to CSV'
    description = Column(Text)                               # Tool description
    icon = Column(String(100))                               # Font Awesome icon class
    url = Column(String(200))                                # Tool URL path
    enabled = Column(Boolean, default=True)                  # Whether tool is available
    
    def __repr__(self):
        return f'<Tool {self.name}>'
