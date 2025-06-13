from sqlalchemy import Column, Integer, String, Text
from models.base import Base

class Config(Base):
    __tablename__ = 'config'
    
    id = Column(Integer, primary_key=True)
    key = Column(String(100), unique=True, nullable=False)
    value = Column(Text, nullable=False)
    description = Column(String(255))
    
    def __repr__(self):
        return f'<Config {self.key}={self.value}>'