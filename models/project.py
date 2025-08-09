from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from .base import Base
from datetime import datetime

class Project(Base):
    __tablename__ = 'project'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False, unique=True)
    description = Column(Text, nullable=True)
    is_default = Column(Boolean, default=False)
    created_by = Column(Integer, ForeignKey('users.id'), nullable=True)  # Project creator
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    creator = relationship("User", foreign_keys=[created_by])
    members = relationship("ProjectMember", back_populates="project", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f'<Project {self.name}>'
    
    def set_as_default(self, session):
        """Set this project as default and unset all others"""
        # First, unset all other projects as default
        session.query(Project).update({Project.is_default: False})
        # Then set this one as default
        self.is_default = True
        session.commit()
    
    def add_member(self, session, user_id, role='member', added_by=None):
        """Add a user as a member to this project"""
        from .project_member import ProjectMember
        
        # Check if user is already a member
        existing = session.query(ProjectMember).filter_by(
            project_id=self.id,
            user_id=user_id,
            is_active=True
        ).first()
        
        if existing:
            return existing
        
        # Create new membership
        membership = ProjectMember(
            project_id=self.id,
            user_id=user_id,
            role=role,
            added_by=added_by
        )
        
        session.add(membership)
        return membership
    
    def remove_member(self, session, user_id):
        """Remove a user from this project"""
        from .project_member import ProjectMember
        
        membership = session.query(ProjectMember).filter_by(
            project_id=self.id,
            user_id=user_id,
            is_active=True
        ).first()
        
        if membership:
            membership.is_active = False
        
        return membership
    
    def get_members(self, session):
        """Get all active members of this project"""
        from .project_member import ProjectMember
        return session.query(ProjectMember).filter_by(
            project_id=self.id,
            is_active=True
        ).all()
    
    def get_owner(self, session):
        """Get the owner of this project"""
        from .project_member import ProjectMember
        return session.query(ProjectMember).filter_by(
            project_id=self.id,
            role='owner',
            is_active=True
        ).first()
    
    @classmethod
    def get_user_projects(cls, session, user_id, include_all_for_admin=False):
        """Get projects accessible to a user"""
        from .project_member import ProjectMember
        from .user import User
        
        if include_all_for_admin:
            # Check if user is admin
            user = session.query(User).get(user_id)
            if user and user.is_admin:
                return session.query(cls).all()
        
        # Get projects where user is a member
        project_ids = session.query(ProjectMember.project_id).filter_by(
            user_id=user_id,
            is_active=True
        ).subquery()
        
        return session.query(cls).filter(cls.id.in_(project_ids)).all()
