from sqlalchemy.orm import sessionmaker
from sqlalchemy import and_, text
import os
from werkzeug.utils import secure_filename
import uuid
from utils.config_utils import initialize_config_table
import sys
parent_dir = ".."
sys.path.append(parent_dir)
# Need to import all model files to create table
import models.artifact
import models.base
import models.config
import models.project
import models.project_config
import models.user
import models.project_member

def create_database(session=None, config=None):
    """
    Create the database and tables if they do not exist.
    """
    if session is None:
        Session = sessionmaker(bind=models.base.engine)
        session = Session()
    
    # Run migration before creating all tables
    migrate_database()
    
    models.base.Base.metadata.create_all(models.base.engine)

    # Types are now managed at project level via project_config table
    # No need to insert global types

    initialize_config_table()

    # Close the session if it was created here
    if session is not None:
        session.close()

def migrate_database():
    """
    Migrate database schema to add new columns and tables
    """
    try:
        Session = sessionmaker(bind=models.base.engine)
        session = Session()
        
        # Check if project table needs migration
        try:
            # Try to select the new column - if it fails, we need to migrate
            session.execute(text("SELECT created_by FROM project LIMIT 1"))
            print("Project table already has new columns")
        except Exception:
            print("Migrating project table...")
            
            # Add missing columns to project table
            try:
                session.execute(text("ALTER TABLE project ADD COLUMN created_by INTEGER"))
                session.commit()
                print("Added created_by column to project table")
            except Exception as e:
                if "duplicate column name" not in str(e).lower():
                    print(f"Warning: Could not add created_by column: {e}")
                session.rollback()
            
            try:
                session.execute(text("ALTER TABLE project ADD COLUMN updated_at DATETIME"))
                session.commit()
                print("Added updated_at column to project table")
            except Exception as e:
                if "duplicate column name" not in str(e).lower():
                    print(f"Warning: Could not add updated_at column: {e}")
                session.rollback()
        
        # Check if project_members table exists
        try:
            session.execute(text("SELECT COUNT(*) FROM project_members LIMIT 1"))
            print("project_members table already exists")
        except Exception:
            print("Creating project_members table...")
            # The table will be created by SQLAlchemy's create_all
        
        # Fix projects without owners - assign first admin user as owner
        try:
            from models.project import Project
            from models.project_member import ProjectMember
            from models.user import User
            
            # Get first admin user
            admin_user = session.query(User).filter_by(is_admin=True).first()
            if admin_user:
                # Find projects without owners
                projects_without_owners = []
                all_projects = session.query(Project).all()
                
                for project in all_projects:
                    owner = session.query(ProjectMember).filter_by(
                        project_id=project.id,
                        role='owner',
                        is_active=True
                    ).first()
                    
                    if not owner:
                        projects_without_owners.append(project)
                
                # Add admin as owner for projects without owners
                for project in projects_without_owners:
                    # Check if admin is already a member
                    existing_membership = session.query(ProjectMember).filter_by(
                        project_id=project.id,
                        user_id=admin_user.id,
                        is_active=True
                    ).first()
                    
                    if existing_membership:
                        # Update existing membership to owner
                        existing_membership.role = 'owner'
                    else:
                        # Create new owner membership
                        owner_membership = ProjectMember(
                            project_id=project.id,
                            user_id=admin_user.id,
                            role='owner',
                            added_by=admin_user.id
                        )
                        session.add(owner_membership)
                    
                    # Set created_by field if not set
                    if not project.created_by:
                        project.created_by = admin_user.id
                
                session.commit()
                print(f"Fixed {len(projects_without_owners)} projects without owners")
            else:
                print("No admin user found - skipping owner assignment")
                
        except Exception as e:
            print(f"Warning: Could not fix project owners: {e}")
            session.rollback()
        
        session.close()
        print("Database migration completed")
        
    except Exception as e:
        print(f"Migration error: {e}")
        if 'session' in locals():
            session.close()

def migrate_user_default_projects():
    """
    Add default_project_id column to users table for per-user default projects
    """
    try:
        Session = sessionmaker(bind=models.base.engine)
        session = Session()
        
        print("=== Migrating User Default Projects ===")
        
        # Check if users table needs migration
        try:
            # Try to select the new column - if it fails, we need to migrate
            session.execute(text("SELECT default_project_id FROM users LIMIT 1"))
            print("Users table already has default_project_id column")
        except Exception:
            print("Adding default_project_id column to users table...")
            
            try:
                session.execute(text("ALTER TABLE users ADD COLUMN default_project_id INTEGER"))
                session.commit()
                print("Added default_project_id column to users table")
            except Exception as e:
                if "duplicate column name" not in str(e).lower():
                    print(f"Warning: Could not add default_project_id column: {e}")
                session.rollback()
        
        session.close()
        print("User default projects migration completed")
        
    except Exception as e:
        print(f"User migration error: {e}")
        if 'session' in locals():
            session.close()

def transfer_project_to_user(project_name, target_username):
    """
    Transfer a project to a specific user by making them the sole owner
    """
    try:
        Session = sessionmaker(bind=models.base.engine)
        session = Session()
        
        # Find the project
        project = session.query(models.project.Project).filter(
            models.project.Project.name.ilike(f'%{project_name}%')
        ).first()
        
        if not project:
            print(f"Project containing '{project_name}' not found")
            session.close()
            return False
            
        # Find the target user
        target_user = session.query(models.user.User).filter(
            models.user.User.username == target_username
        ).first()
        
        if not target_user:
            print(f"User '{target_username}' not found")
            session.close()
            return False
            
        print(f"Transferring project '{project.name}' to user '{target_username}'...")
        
        # Update the project's created_by field
        project.created_by = target_user.id
        
        # Remove all existing project members
        existing_members = session.query(models.project_member.ProjectMember).filter_by(
            project_id=project.id
        ).all()
        
        for member in existing_members:
            member.is_active = False
            
        # Add target user as the sole owner
        new_membership = models.project_member.ProjectMember(
            project_id=project.id,
            user_id=target_user.id,
            role='owner',
            added_by=target_user.id,
            is_active=True
        )
        session.add(new_membership)
        
        session.commit()
        print(f"Successfully transferred project '{project.name}' to '{target_username}'")
        session.close()
        return True
        
    except Exception as e:
        print(f"Error transferring project: {e}")
        if 'session' in locals():
            session.rollback()
            session.close()
        return False

def get_unique_filename(filename):
    """Generate unique filename while preserving extension"""
    ext = os.path.splitext(filename)[1]
    return f"{uuid.uuid4().hex}{ext}"

def save_image(file, config):
    """Save image to disk and return relative path"""
    filename = secure_filename(file.filename)
    unique_name = get_unique_filename(filename)
    
    # Create upload directory if it doesn't exist
    upload_path = os.path.join(os.path.dirname(__file__), config['storage']['image_path'])
    os.makedirs(upload_path, exist_ok=True)
    
    # Save file
    file_path = os.path.join(upload_path, unique_name)
    file.save(file_path)
    
    # Return relative path for database storage
    return os.path.join(config['storage']['image_path'], unique_name)

def delete_image(image_path):
    """Delete image from disk"""
    full_path = os.path.join(os.path.dirname(__file__), image_path)
    if os.path.exists(full_path):
        os.remove(full_path)


