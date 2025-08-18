from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from .base import Base
from datetime import datetime

class ProjectMember(Base):
    """Association table for users and projects with additional metadata"""
    __tablename__ = 'project_members'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(Integer, ForeignKey('project.id'), nullable=False)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    role = Column(String(50), default='member', nullable=False)  # 'owner', 'member'
    added_by = Column(Integer, ForeignKey('users.id'), nullable=True)  # Who added this user
    added_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Relationships
    project = relationship("Project", back_populates="members")
    user = relationship("User", foreign_keys=[user_id], back_populates="project_memberships")
    added_by_user = relationship("User", foreign_keys=[added_by])
    
    def __repr__(self):
        return f'<ProjectMember user_id={self.user_id} project_id={self.project_id} role={self.role}>'
    
    @classmethod
    def get_user_projects(cls, session, user_id):
        """Get all projects where user is a member"""
        return session.query(cls).filter_by(user_id=user_id, is_active=True).all()
    
    @classmethod
    def get_project_members(cls, session, project_id):
        """Get all members of a project"""
        return session.query(cls).filter_by(project_id=project_id, is_active=True).all()
    
    @classmethod
    def is_user_member(cls, session, user_id, project_id):
        """Check if user is a member of the project"""
        return session.query(cls).filter_by(
            user_id=user_id, 
            project_id=project_id, 
            is_active=True
        ).first() is not None
    
    @classmethod
    def is_user_owner(cls, session, user_id, project_id):
        """Check if user is the owner of the project"""
        membership = session.query(cls).filter_by(
            user_id=user_id, 
            project_id=project_id, 
            is_active=True,
            role='owner'
        ).first()
        return membership is not None
