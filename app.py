from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, make_response, abort, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from datetime import datetime, date
import os
import utility
import yaml
from sqlalchemy.orm import sessionmaker
import base64
from werkzeug.utils import secure_filename
from markdown2 import Markdown
from utility import save_image, delete_image
from dotenv import load_dotenv
from utils.config_utils import load_config, update_config, get_config_for_settings, get_section_title, get_section_icon, reset_config_to_defaults
from utils.auth_utils import admin_required, active_user_required, get_safe_redirect_url, init_default_admin, validate_user_data, check_unique_user_fields, format_user_for_display
from utils.project_config_utils import get_project_config, initialize_project_configs

from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image as RLImage, PageBreak, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, cm
from reportlab.lib import colors
from reportlab.lib.enums import TA_JUSTIFY, TA_CENTER, TA_LEFT
from reportlab.platypus.flowables import HRFlowable
import io
import os
import re
from PIL import Image as PILImage

from datetime import datetime
import sys

# Path setup
parent_dir = ".."
sys.path.append(parent_dir)
sys.path.append('/app')

# Import models
import models.base
import models.artifact
import models.config
import models.project
import models.project_member
import models.project_config
import models.user

load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('FLASK_SECRET_KEY')

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Please log in to access this page.'
login_manager.login_message_category = 'info'

@login_manager.user_loader
def load_user(user_id):
    """Load user for Flask-Login"""
    return session.query(User).get(int(user_id))

# Create instance directory if it doesn't exist
instance_path = '/app/instance'
os.makedirs(instance_path, exist_ok=True)

# Declare config as global at module level
config = None

# Load config from database instead of YAML
def initialize_config():
    global config
    config = load_config()

# Initialize config
initialize_config()

# Create database if it doesn't exist
utility.create_database(config=config)

# Run database migration to add new columns
# try:
#     utility.migrate_database()
#     utility.migrate_user_default_projects()
# except Exception as e:
#     print(f"Warning: Migration failed: {e}")

Session = sessionmaker(bind=models.base.engine)
session = Session()
Artifact = models.artifact.Artifact
Project = models.project.Project
User = models.user.User
ProjectMember = models.project_member.ProjectMember

# Initialize default admin user if no users exist
init_default_admin(session, User)

# Make date available in templates
@app.context_processor
def inject_date():
    return {'today': date.today()}

@app.context_processor
def inject_helpers():
    return dict(
        get_section_title=get_section_title,
        get_section_icon=get_section_icon,
        today=date.today(),
        config=config
    )

@app.context_processor
def inject_navigation_context():
    """Inject navigation-specific context including project-level types"""
    if not current_user.is_authenticated:
        return {}
    
    # Get current project context from request args
    project_filter = request.args.get('project', '')
    current_project_id = None
    
    if project_filter == 'default':
        current_project_id = get_user_default_project_id()
    elif project_filter and project_filter != 'all':
        try:
            current_project_id = int(project_filter)
        except (ValueError, TypeError):
            current_project_id = None
    
    # Get appropriate types for navigation
    if current_project_id:
        # Single project - use its specific types
        nav_types = get_project_types(current_project_id)
    else:
        # All projects or no specific project - collect all types from user's accessible projects
        nav_types = get_all_user_project_types()
    
    # Get projects for navigation
    nav_projects = get_all_projects()
    
    return {
        'nav_types': nav_types,
        'nav_projects': nav_projects
    }

@app.context_processor
def inject_user_stats():
    """Inject user statistics for navigation display"""
    if not current_user.is_authenticated:
        return {'user_artifact_count': 0}
    
    try:
        # Get count of artifacts accessible to the current user
        accessible_project_ids = get_user_accessible_project_ids()
        artifact_count = session.query(Artifact).filter(
            Artifact.project_id.in_(accessible_project_ids),
            Artifact.deleted == False
        ).count()
        
        return {'user_artifact_count': artifact_count}
    except Exception:
        return {'user_artifact_count': 0}

# Create markdown renderer
markdowner = Markdown(extras=["tables", "fenced-code-blocks"])

@app.template_filter('markdown')
def markdown_filter(text):
    return markdowner.convert(text)

# Authentication Routes
@app.route('/login', methods=['GET', 'POST'])
def login():
    """User login page"""
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        remember_me = request.form.get('remember_me') == 'on'
        
        if not username or not password:
            flash('Please enter both username and password.', 'error')
            return render_template('login.html')
        
        # Find user by username
        user = session.query(User).filter(User.username == username).first()
        
        if user and user.check_password(password):
            if not user.is_active:
                flash('Your account has been deactivated. Please contact an administrator.', 'error')
                return render_template('login.html')
            
            # Update last login time
            user.update_last_login()
            session.commit()
            
            # Log in the user
            login_user(user, remember=remember_me)
            
            flash(f'Welcome back, {user.full_name}!', 'success')
            
            # Redirect to next page or index
            next_page = request.args.get('next')
            return redirect(get_safe_redirect_url(next_page))
        else:
            flash('Invalid username or password.', 'error')
    
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    """User logout"""
    logout_user()
    flash('You have been logged out successfully.', 'info')
    return redirect(url_for('login'))

@app.route('/settings', methods=['GET', 'POST'])
@login_required
@active_user_required
def settings():
    global config
    
    if request.method == 'POST':
        # Check if this is a reset request
        if 'reset_defaults' in request.form:
            try:
                if reset_config_to_defaults():
                    flash('Configuration reset to default values successfully!', 'success')
                    # Reload config
                    config = load_config()
                else:
                    flash('Error resetting configuration to defaults.', 'error')
            except Exception as e:
                flash(f'Error resetting configuration: {str(e)}', 'error')
            
            return redirect(url_for('settings'))
        
        # Normal settings update
        try:
            # Load YAML config to check editability
            from utils.config_utils import load_config_from_yaml, flatten_dict
            yaml_config = load_config_from_yaml()
            flat_config = flatten_dict(yaml_config)
            
            # Create a map of config keys to their editability
            editability_map = {}
            for key, value, is_editable in flat_config:
                editability_map[key] = is_editable
            
            # Get all form data
            updates = {}
            for key in request.form:
                if key == 'reset_defaults':  # Skip reset button
                    continue
                
                # Check if this config item is editable
                if not editability_map.get(key, True):
                    # Skip non-editable items
                    continue
                    
                value = request.form[key]
                
                # Convert values to appropriate types based on key patterns
                if key.endswith(('_port', '_size', '_days', '_hours', '_notifications', '_interval', '_backups')) or key.split('.')[-1] in ['max_file_size', 'smtp_port', 'notification_days', 'max_notifications', 'notification_interval', 'cleanup_threshold_hours', 'keep_backups']:
                    value = int(value)
                elif value.lower() in ('true', 'false'):
                    value = value.lower() == 'true'
                elif key == 'type' or key.endswith('.allowed_extensions'):
                    # Handle arrays
                    value = [t.strip() for t in value.split(',') if t.strip()]
                
                updates[key] = value
            
            # Update each config item
            success_count = 0
            for key, value in updates.items():
                if update_config(key, value):
                    success_count += 1
            
            if success_count > 0:
                flash(f'Successfully updated {success_count} configuration(s)!', 'success')
                # Reload config
                config = load_config()
            else:
                flash('No configurations were updated.', 'error')
                
        except Exception as e:      
            flash(f'Error updating configuration: {str(e)}', 'error')
        
        return redirect(url_for('index'))
    
    # Get all config items for display
    config_items = get_config_for_settings()
    
    # Get user management data if user is admin
    
    return render_template('settings.html', config_items=config_items)

@app.route('/user-management')
@login_required
@active_user_required
@admin_required
def user_management():
    """User management page (admin only)"""
    # Get all users for display
    all_users = session.query(User).order_by(User.created_at.desc()).all()
    users_data = [format_user_for_display(user) for user in all_users]
    
    return render_template('user_management.html', users_data=users_data)

# User Management Routes (Admin Only)
@app.route('/users/add', methods=['POST'])
@login_required
@active_user_required
@admin_required
def add_user():
    """Add new user (admin only)"""
    username = request.form.get('username', '').strip()
    email = request.form.get('email', '').strip()
    password = request.form.get('password', '')
    full_name = request.form.get('full_name', '').strip()
    is_admin = request.form.get('is_admin') == 'on'
    is_active = request.form.get('is_active') == 'on'
    notes = request.form.get('notes', '').strip()
    
    # Validate input data
    errors = validate_user_data(username, email, password, full_name)
    if errors:
        for error in errors:
            flash(error, 'error')
        return redirect(url_for('user_management'))
    
    # Check uniqueness
    unique_errors = check_unique_user_fields(session, User, username, email)
    if unique_errors:
        for error in unique_errors:
            flash(error, 'error')
        return redirect(url_for('user_management'))
    
    try:
        # Create new user
        new_user = User(
            username=username,
            email=email,
            password=password,
            full_name=full_name,
            is_admin=is_admin,
            is_active=is_active,
            notes=notes or None
        )
        
        session.add(new_user)
        session.commit()
        
        flash(f'User "{username}" created successfully!', 'success')
        
    except Exception as e:
        session.rollback()
        flash(f'Error creating user: {str(e)}', 'error')
    
    return redirect(url_for('user_management'))

@app.route('/users/<int:user_id>/edit', methods=['GET', 'POST'])
@login_required
@active_user_required
@admin_required
def edit_user(user_id):
    """Edit existing user (admin only)"""
    user = session.query(User).get(user_id)
    if not user:
        flash('User not found.', 'error')
        return redirect(url_for('user_management'))
    
    if request.method == 'GET':
        # Show edit form
        return render_template('edit_user.html', user=user)
    
    # Handle POST request (form submission)
    # Prevent admin from disabling their own account
    if user.id == current_user.id and request.form.get('is_active') != 'on':
        flash('You cannot deactivate your own account.', 'error')
        return redirect(url_for('user_management'))
    
    username = request.form.get('username', '').strip()
    email = request.form.get('email', '').strip()
    password = request.form.get('password', '')
    full_name = request.form.get('full_name', '').strip()
    is_admin = request.form.get('is_admin') == 'on'
    is_active = request.form.get('is_active') == 'on'
    notes = request.form.get('notes', '').strip()
    
    # Validate input data
    errors = validate_user_data(username, email, password, full_name, is_editing=True)
    if errors:
        for error in errors:
            flash(error, 'error')
        return redirect(url_for('user_management'))
    
    # Check uniqueness (excluding current user)
    unique_errors = check_unique_user_fields(session, User, username, email, exclude_user_id=user_id)
    if unique_errors:
        for error in unique_errors:
            flash(error, 'error')
        return redirect(url_for('user_management'))
    
    try:
        # Update user
        user.username = username
        user.email = email
        user.full_name = full_name
        user.is_admin = is_admin
        user.is_active = is_active
        user.notes = notes or None
        
        # Update password if provided
        if password:
            user.set_password(password)
        
        session.commit()
        
        flash(f'User "{username}" updated successfully!', 'success')
        
    except Exception as e:
        session.rollback()
        flash(f'Error updating user: {str(e)}', 'error')
    
    return redirect(url_for('user_management'))

@app.route('/users/<int:user_id>/delete', methods=['POST'])
@login_required
@active_user_required
@admin_required
def delete_user(user_id):
    """Delete user (admin only)"""
    user = session.query(User).get(user_id)
    if not user:
        flash('User not found.', 'error')
        return redirect(url_for('user_management'))
    
    # Prevent admin from deleting their own account
    if user.id == current_user.id:
        flash('You cannot delete your own account.', 'error')
        return redirect(url_for('user_management'))
    
    # Check if this is the last admin user
    admin_count = session.query(User).filter(User.is_admin == True, User.is_active == True).count()
    if user.is_admin and admin_count <= 1:
        flash('Cannot delete the last active admin user.', 'error')
        return redirect(url_for('user_management'))
    
    try:
        username = user.username
        session.delete(user)
        session.commit()
        
        flash(f'User "{username}" deleted successfully!', 'success')
        
    except Exception as e:
        session.rollback()
        flash(f'Error deleting user: {str(e)}', 'error')
    
    return redirect(url_for('user_management'))

@app.route('/get_project_types')
@login_required
@active_user_required
def get_project_types_api():
    """API endpoint to get types for a specific project or all projects"""
    project_filter = request.args.get('project', '')
    current_project_id = None
    
    if project_filter == 'default':
        current_project_id = get_user_default_project_id()
    elif project_filter and project_filter != 'all':
        try:
            current_project_id = int(project_filter)
        except (ValueError, TypeError):
            current_project_id = None
    
    # Get appropriate types
    if current_project_id:
        # Single project - use its specific types
        types = get_project_types(current_project_id)
    else:
        # All projects or no specific project - collect all types from user's accessible projects
        types = get_all_user_project_types()
    
    return jsonify({'types': types})

def get_project_types(project_id):
    """Get types for a specific project from project_config"""
    if not project_id:
        return []
    
    # Get types from project config
    types_list = get_project_config(project_id, 'type', [])
    if not types_list:
        # Return empty list if no project-specific types configured
        return []
    
    # Create list of dicts with id as index and name from project config
    return [{'id': str(i), 'name': type_name} for i, type_name in enumerate(types_list)]

def get_all_user_project_types():
    """Get all unique types from all projects accessible to the user"""
    accessible_project_ids = get_user_accessible_project_ids()
    all_types = set()
    
    for project_id in accessible_project_ids:
        project_types = get_project_types(project_id)
        for type_obj in project_types:
            all_types.add(type_obj['name'])
    
    # If no types found from projects, return empty list
    if not all_types:
        return []
    
    # Convert to list of dicts with sequential IDs
    return [{'id': str(i), 'name': type_name} for i, type_name in enumerate(sorted(all_types))]

@app.route('/')
@login_required
@active_user_required
def index():
    type_filter = request.args.get('type', '')  # Changed to empty string default
    project_filter = request.args.get('project', 'default')  # Default to showing default project
    show_all = request.args.get('type') == 'all'
    
    # Determine current project ID for type filtering
    current_project_id = None
    if project_filter == 'default':
        current_project_id = get_user_default_project_id()
    elif project_filter and project_filter != 'all':
        current_project_id = int(project_filter)
    
    # Get project-specific types for dropdown
    if current_project_id:
        # Single project - use its specific types
        project_types = get_project_types(current_project_id)
        types_dict = {t['id']: t['name'] for t in project_types}
        types = project_types
    else:
        # All projects or no specific project - collect all types from user's accessible projects
        all_user_types = get_all_user_project_types()
        types_dict = {t['id']: t['name'] for t in all_user_types}
        types = all_user_types
    
    # Get default type from project config if no type filter is specified and not showing all
    if not type_filter and not show_all and current_project_id:
        default_type_name = get_project_config(current_project_id, 'default_type', 'Token')
        # Find the type in project types
        for type_obj in project_types:
            if type_obj['name'] == default_type_name:
                type_filter = type_obj['id']
                break
    elif not type_filter and not show_all:
        # Use project default type if available
        default_type_name = get_project_config(current_project_id, 'default_type', '') if current_project_id else ''
        if default_type_name:
            # Find the type in current types
            for type_id, type_name in types_dict.items():
                if type_name == default_type_name:
                    type_filter = type_id
                    break
    
    # Start with base query - no search filtering on index page
    query = session.query(Artifact).filter(Artifact.deleted == False)
    
    # Apply type filter only if specifically selected and not showing all
    if type_filter and not show_all:
        # Get the type name from the types dictionary
        type_name = types_dict.get(type_filter)
        if type_name:
            # Filter by type_name directly
            query = query.filter(Artifact.type_name == type_name)
    
    # Apply project filter
    if project_filter == 'default':
        # Show only user's personal default project artifacts, but only if user has access
        user_default_project_id = get_user_default_project_id()
        if user_default_project_id and user_has_project_access(user_default_project_id):
            query = query.filter(Artifact.project_id == user_default_project_id)
        else:
            # User doesn't have a personal default project or access to it, show no artifacts
            query = query.filter(Artifact.id == -1)
    elif project_filter and project_filter != 'all':
        # Show specific project artifacts
        query = query.filter(Artifact.project_id == project_filter)
    else:
        # If project_filter is 'all' or not specified, show only artifacts from accessible projects
        accessible_project_ids = get_user_accessible_project_ids()
        if accessible_project_ids:
            query = query.filter(Artifact.project_id.in_(accessible_project_ids))
        else:
            # User has no accessible projects, show no artifacts
            query = query.filter(Artifact.id == -1)
    
    # Get final results
    artifacts = query.order_by(Artifact.expiry_date.asc()).all()
    
    # Get projects for dropdown
    projects = get_all_projects()
    default_project = get_user_default_project()
    
    return render_template('index.html', 
                         artifacts=artifacts,
                         type_filter=type_filter if not show_all else '',
                         project_filter=project_filter,
                         show_all=show_all,
                         today=date.today(),
                         types=types,
                         projects=projects,
                         default_project=default_project,
                         config=config,
                         types_dict=types_dict)

@app.route('/search')
@login_required
@active_user_required
def search():
    search_query = request.args.get('search', '').strip()
    type_filter = request.args.get('type', '')
    project_filter = request.args.get('project', '')  # New project filter
    
    # Determine current project ID for type filtering
    current_project_id = None
    if project_filter == 'default':
        current_project_id = get_user_default_project_id()
    elif project_filter and project_filter != 'all':
        current_project_id = int(project_filter)
    
    # Get project-specific types for dropdown
    if current_project_id:
        # Single project - use its specific types
        project_types = get_project_types(current_project_id)
        types_dict = {t['id']: t['name'] for t in project_types}
        types = project_types
    else:
        # All projects or no specific project - collect all types from user's accessible projects
        all_user_types = get_all_user_project_types()
        types_dict = {t['id']: t['name'] for t in all_user_types}
        types = all_user_types
    
    # Start with base query
    query = session.query(Artifact).filter(Artifact.deleted == False)
    
    # Apply search filter if present
    if search_query:
        name_results = query.filter(Artifact.name.ilike(f'%{search_query}%'))
        content_results = query.filter(Artifact.content.ilike(f'%{search_query}%'))
        query = name_results.union(content_results)
    else:
        # If no search query, return empty results to encourage searching
        query = query.filter(Artifact.id == -1)  # This will return no results
    
    # Apply type filter only if specifically selected
    if type_filter:
        # Get the type name from the types dictionary
        type_name = types_dict.get(type_filter)
        if type_name:
            # Filter by type_name directly
            query = query.filter(Artifact.type_name == type_name)
    
    # Apply project filter
    if project_filter == 'default':
        # Search only in user's personal default project, but only if user has access
        user_default_project_id = get_user_default_project_id()
        if user_default_project_id and user_has_project_access(user_default_project_id):
            query = query.filter(Artifact.project_id == user_default_project_id)
        else:
            # User doesn't have a personal default project or access to it, show no artifacts
            query = query.filter(Artifact.id == -1)
    elif project_filter and project_filter != 'all':
        # Search in specific project
        query = query.filter(Artifact.project_id == project_filter)
    else:
        # If project_filter is 'all' or empty, search only in accessible projects
        accessible_project_ids = get_user_accessible_project_ids()
        if accessible_project_ids:
            query = query.filter(Artifact.project_id.in_(accessible_project_ids))
        else:
            # User has no accessible projects, show no artifacts
            query = query.filter(Artifact.id == -1)
    
    # Get final results
    artifacts = query.order_by(Artifact.expiry_date.asc()).all()
    
    # Get projects for dropdown
    projects = get_all_projects()
    default_project = get_user_default_project()
    
    return render_template('search.html', 
                         artifacts=artifacts,
                         search_query=search_query,
                         type_filter=type_filter,
                         project_filter=project_filter,
                         today=date.today(),
                         types=types,
                         projects=projects,
                         default_project=default_project,
                         config=config,
                         types_dict=types_dict)


@app.route('/add', methods=['GET', 'POST'])
@login_required
@active_user_required
def add_artifact():
    if request.method == 'POST':
        images_data = []  # Initialize before try block
        try:
            # Get form data
            name = request.form['name']
            type_name = request.form['type']  # Changed from 'artifact_type' to 'type'
            content = request.form['content']
            date_created_str = request.form.get('expiry_date')  # Changed back to 'expiry_date'
            
            # Handle expiry date
            expiry_date = None
            if date_created_str:
                expiry_date = datetime.strptime(date_created_str, '%Y-%m-%d').date()
            
            # Handle image uploads
            files = request.files.getlist('images')  # Changed from 'images[]' to 'images'
            
            for file in files:
                if file and file.filename:
                    if not file.content_type.startswith('image/'):
                        raise ValueError(f"Invalid file type: {file.filename}")
                    
                    # Check file size if config is available
                    try:
                        if file.content_length and file.content_length > config['storage']['max_file_size']:
                            raise ValueError(f"File too large: {file.filename}")
                    except (KeyError, TypeError):
                        # If config not available, skip size check
                        pass
                    
                    # Save image and store metadata
                    relative_path = save_image(file, config)
                    images_data.append({
                        'name': file.filename,
                        'path': relative_path
                    })
            
            # Get project assignment (use form value or user's accessible default)
            project_id = request.form.get('project_id')
            if not project_id:
                project_id = get_user_default_project_id()
            
            # Validate that the type_name is valid for the project
            project_types = get_project_types(project_id)
            valid_type = False
            for type_obj in project_types:
                if type_obj['name'] == type_name:
                    valid_type = True
                    break
            
            if not valid_type:
                raise ValueError("Invalid type selection")
            
            # Create artifact with image metadata using type_name
            artifact = Artifact(
                name=name,
                type_name=type_name,  # Use project-level type name directly
                content=content,
                expiry_date=expiry_date,  # Use correct field name from model
                project_id=project_id,
                images=images_data
            )
            
            session.add(artifact)
            session.commit()
            
            flash('Artifact created successfully!', 'success')
            return redirect(url_for('artifact_detail', artifact_id=artifact.id))
            
        except Exception as e:
            # Delete any saved images if artifact creation fails
            if images_data:  # Check if images_data has content before iterating
                for image in images_data:
                    try:
                        delete_image(image['path'])
                    except Exception:
                        # Ignore cleanup errors
                        pass
            flash(str(e), 'error')
            session.rollback()
    
    # GET request - show form
    # Get user's default project for type filtering
    default_project_id = get_user_default_project_id()
    
    # Get project-specific types
    if default_project_id:
        project_types = get_project_types(default_project_id)
        types = project_types
        default_type_name = get_project_config(default_project_id, 'default_type', 'Token')
    else:
        # Use empty types list if no default project
        types = []
        default_type_name = 'Token'
    
    projects = get_all_projects()
    
    # Find the ID of the default type
    default_type_id = None
    for type_obj in types:
        if type_obj['name'] == default_type_name:
            default_type_id = type_obj['id']
            break
    
    return render_template('add_artifact.html', 
                         types=types, 
                         projects=projects,
                         default_type_id=default_type_id,
                         default_project_id=get_user_default_project_id())

@app.route('/delete/<int:artifact_id>', methods=['POST'])
@login_required
@active_user_required
def delete_artifact(artifact_id):
    artifact = session.query(Artifact).get(artifact_id)
    if not artifact:
        flash('Artifact not found!', 'error')
        return redirect(url_for('index'))
    
    # Check if user has access to this artifact's project
    if not user_has_project_access(artifact.project_id):
        flash('You do not have access to delete this artifact.', 'error')
        return redirect(url_for('index'))
    
    # Soft delete instead of hard delete
    artifact.soft_delete()
    session.commit()
    flash('Artifact has been moved to trash', 'info')
    return redirect(url_for('index'))

@app.route('/update/<int:artifact_id>', methods=['GET', 'POST'])
@login_required
@active_user_required
def update_artifact(artifact_id):
    artifact = session.query(Artifact).filter(Artifact.id==artifact_id).first()
    if not artifact:
        flash('Artifact not found!', 'error')
        return redirect(url_for('index'))
    
    # Check if user has access to this artifact's project
    if not user_has_project_access(artifact.project_id):
        flash('You do not have access to edit this artifact.', 'error')
        return redirect(url_for('index'))
    if request.method == 'POST':
        try:
            # Validate required fields
            if not request.form.get('name'):
                raise ValueError("Name is required")
            if not request.form.get('content'):
                raise ValueError("Content is required")
            if not request.form.get('type'):
                raise ValueError("Type is required")
            
            # Update basic info
            artifact.name = request.form['name']
            artifact.content = request.form['content']
            
            # Handle project change (only for admins)
            target_project_id = artifact.project_id  # Default to current project
            if current_user.is_admin and 'project_id' in request.form:
                new_project_id = request.form['project_id']
                if new_project_id != str(artifact.project_id):
                    # Verify admin has access to the new project
                    if user_has_project_access(int(new_project_id)):
                        target_project_id = int(new_project_id)
                        artifact.project_id = target_project_id
                        flash('Artifact moved to different project.', 'info')
            
            # Convert project-specific type name to validate against project types
            type_name = request.form['type']
            project_types = get_project_types(target_project_id)
            
            # If no project types are configured, accept any type
            if not project_types:
                artifact.type_name = type_name
            else:
                # Validate type against project types
                valid_type = False
                for type_obj in project_types:
                    if type_obj['name'] == type_name:
                        valid_type = True
                        break
                
                # Update artifact type using type_name
                if valid_type:
                    artifact.type_name = type_name
                else:
                    raise ValueError(f"Invalid type selection: '{type_name}' not found in project types")
            
            # Handle expiry date
            expiry_date = None
            if request.form.get('expiry_date'):
                expiry_date = datetime.strptime(request.form['expiry_date'], '%Y-%m-%d').date()
            artifact.expiry_date = expiry_date

            # Initialize images array if None
            if artifact.images is None:
                artifact.images = []
            else:
                # Convert to list if it's not already
                artifact.images = list(artifact.images)

            # Handle removed images
            removed_images_list = []
            for key in request.form.keys():
                if key.startswith('removed_images'):
                    removed_images_list.extend(request.form.getlist(key))
            
            if removed_images_list:
                for img in artifact.images[:]:
                    if str(img.get('id', '')) in removed_images_list or img.get('name', '') in removed_images_list:
                        delete_image(img['path'])
                        artifact.images.remove(img)

            # Handle new images
            files = request.files.getlist('images')
            if files:
                for file in files:
                    if file and file.filename:
                        if not file.content_type.startswith('image/'):
                            raise ValueError(f"Invalid file type: {file.filename}")
                        
                        # Check file size if content_length is available
                        if hasattr(file, 'content_length') and file.content_length and file.content_length > config['storage']['max_file_size']:
                            raise ValueError(f"File too large: {file.filename}")
                        
                        # Save new image
                        relative_path = save_image(file, config)
                        if not artifact.images:
                            artifact.images = []
                        artifact.images.append({
                            'name': file.filename,
                            'path': relative_path
                        })
            
            session.add(artifact)
            session.commit()
            
            flash('Artifact updated successfully!', 'success')
            return redirect(url_for('artifact_detail', artifact_id=artifact.id))
            
        except Exception as e:
            print(f"DEBUG: Error updating artifact: {str(e)}")
            print(f"DEBUG: Form data: {dict(request.form)}")
            print(f"DEBUG: Files: {[f.filename for f in request.files.getlist('images')]}")
            flash(str(e), 'error')
            session.rollback()

    # Get project-specific types for the artifact's project
    project_types = get_project_types(artifact.project_id)
    types = project_types
    
    # Get current artifact's type name for template selection
    current_type_name = artifact.get_type_name()
    
    projects = get_all_projects()
    return render_template('update_artifact.html',
                         artifact=artifact, 
                         types=types,
                         projects=projects,
                         current_type_name=current_type_name,
                         is_admin=current_user.is_admin)

@app.route('/artifact/<int:artifact_id>')
@login_required
@active_user_required
def artifact_detail(artifact_id):
    artifact = session.query(Artifact).filter(Artifact.id==artifact_id).first()
    if not artifact:
        flash('Artifact not found!', 'error')
        return redirect(url_for('index'))
    
    # Check if user has access to this artifact's project
    if not user_has_project_access(artifact.project_id):
        flash('You do not have access to this artifact.', 'error')
        return redirect(url_for('index'))
    
    # Get type name using the new method
    type_name = artifact.get_type_name()
    
    # Get project information
    project = session.query(Project).filter(Project.id==artifact.project_id).first()
    
    # Calculate status
    if artifact.expiry_date is None:
        days_until_expiry = None
        status_badge = "bg-secondary"
        status_text = "No Expiry Date"
        status_icon = "fas fa-calendar-times"
    else:
        days_until_expiry = (artifact.expiry_date - date.today()).days
        if artifact.is_expired():
            status_badge = "bg-danger"
            status_text = "Expired"
            status_icon = "fas fa-times-circle"
        elif days_until_expiry <= 14:
            status_badge = "bg-warning text-dark"
            status_text = "Expires Soon"
            status_icon = "fas fa-exclamation-triangle"
        else:
            status_badge = "bg-success"
            status_text = "Active"
            status_icon = "fas fa-check-circle"
    
    return render_template('artifact_detail.html', 
                         artifact=artifact,
                         type_name=type_name,
                         days_until_expiry=days_until_expiry,
                         status_badge=status_badge,
                         status_text=status_text,
                         status_icon=status_icon,
                         config=config,
                         project=project)


@app.route('/static/uploads/<path:filename>')
def serve_image(filename):
    return send_from_directory(config['storage']['image_path'], filename)

def clean_markdown_for_pdf(text):
    """Convert markdown to PDF-friendly text with basic formatting"""
    if not text:
        return ""
    
    # Convert markdown to HTML first using markdowner
    html = markdowner.convert(text)
    
    # Clean HTML tags for reportlab
    html = re.sub(r'<h1>(.*?)</h1>', r'<para fontSize="18" spaceAfter="12"><b>\1</b></para>', html)
    html = re.sub(r'<h2>(.*?)</h2>', r'<para fontSize="16" spaceAfter="10"><b>\1</b></para>', html)
    html = re.sub(r'<h3>(.*?)</h3>', r'<para fontSize="14" spaceAfter="8"><b>\1</b></para>', html)
    html = re.sub(r'<h4>(.*?)</h4>', r'<para fontSize="12" spaceAfter="6"><b>\1</b></para>', html)
    html = re.sub(r'<strong>(.*?)</strong>', r'<b>\1</b>', html)
    html = re.sub(r'<em>(.*?)</em>', r'<i>\1</i>', html)
    html = re.sub(r'<code>(.*?)</code>', r'<font name="Courier">\1</font>', html)
    html = re.sub(r'<pre><code>(.*?)</code></pre>', r'<para backColor="#f0f0f0" borderPadding="10"><font name="Courier">\1</font></para>', html, flags=re.DOTALL)
    html = re.sub(r'<blockquote>(.*?)</blockquote>', r'<para leftIndent="20" borderWidth="2" borderColor="#3498db" borderPadding="10"><i>\1</i></para>', html, flags=re.DOTALL)
    html = re.sub(r'<ul>', '', html)
    html = re.sub(r'</ul>', '', html)
    html = re.sub(r'<ol>', '', html)
    html = re.sub(r'</ol>', '', html)
    html = re.sub(r'<li>(.*?)</li>', r'• \1<br/>', html)
    html = re.sub(r'<p>(.*?)</p>', r'<para spaceAfter="10">\1</para>', html, flags=re.DOTALL)
    html = re.sub(r'<br\s*/?>', '<br/>', html)
    
    # Remove any remaining HTML tags
    html = re.sub(r'<[^>]+>', '', html)
    
    return html

@app.route('/artifact/<int:artifact_id>/export/pdf')
@login_required
@active_user_required
def export_artifact_pdf(artifact_id):
    artifact = session.query(Artifact).filter_by(id=artifact_id).first()
    if not artifact:
        abort(404)
    
    # Check if user has access to this artifact's project
    if not user_has_project_access(artifact.project_id):
        flash('You do not have access to export this artifact.', 'error')
        return redirect(url_for('index'))
    
    try:
        # Create PDF buffer
        buffer = io.BytesIO()
        
        # Create PDF document
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=2*cm,
            leftMargin=2*cm,
            topMargin=2*cm,
            bottomMargin=2*cm
        )
        
        # Get sample styles
        styles = getSampleStyleSheet()

        # Define custom styles
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Title'],
            fontSize=24,
            textColor=colors.HexColor('#2c3e50'),
            alignment=TA_CENTER,
            spaceAfter=30,
            fontName='Helvetica-Bold'
        )
        
        type_style = ParagraphStyle(
            'TypeBadge',
            parent=styles['Normal'],
            fontSize=12,
            textColor=colors.white,
            backColor=colors.HexColor('#3498db'),
            alignment=TA_CENTER,
            borderPadding=8,
            spaceAfter=20,
            fontName='Helvetica-Bold'
        )
        
        meta_style = ParagraphStyle(
            'MetaInfo',
            parent=styles['Normal'],
            fontSize=11,
            textColor=colors.HexColor('#666666'),
            spaceAfter=15,
            fontName='Helvetica'
        )

        content_style = ParagraphStyle(
            'ContentStyle',
            parent=styles['Normal'],
            fontSize=12,
            alignment=TA_JUSTIFY,
            spaceAfter=12,
            leading=18,
            fontName='Times-Roman'
        )
        
        heading_style = ParagraphStyle(
            'HeadingStyle',
            parent=styles['Heading2'],
            fontSize=16,
            textColor=colors.HexColor('#2c3e50'),
            spaceAfter=12,
            spaceBefore=20,
            fontName='Helvetica-Bold'
        )
        
        warning_style = ParagraphStyle(
            'WarningStyle',
            parent=styles['Normal'],
            fontSize=12,
            textColor=colors.white,
            backColor=colors.HexColor('#f39c12'),
            alignment=TA_CENTER,
            borderPadding=10,
            spaceAfter=20,
            fontName='Helvetica-Bold'
        )

        expired_style = ParagraphStyle(
            'ExpiredStyle',
            parent=styles['Normal'],
            fontSize=12,
            textColor=colors.white,
            backColor=colors.HexColor('#e74c3c'),
            alignment=TA_CENTER,
            borderPadding=10,
            spaceAfter=20,
            fontName='Helvetica-Bold'
        )
        
        # Build PDF content
        story = []
        
        # Title
        story.append(Paragraph(artifact.name, title_style))
        
        # Horizontal line after title
        story.append(HRFlowable(width="100%", thickness=2, color=colors.HexColor('#2c3e50')))
        story.append(Spacer(1, 20))

        # Type badge
        type_name = artifact.get_type_name()
        story.append(Paragraph(f"Type: {type_name}", type_style))
        
        # Meta information table
        meta_data = []
        created_date = artifact.created_at.strftime("%B %d, %Y at %I:%M %p")
        meta_data.append(['Created:', created_date])
        
        if artifact.expiry_date:
            expiry_date = artifact.expiry_date.strftime("%B %d, %Y")
            days_remaining = (artifact.expiry_date - datetime.now().date()).days
            meta_data.append(['Expires:', expiry_date])
            meta_data.append(['Days Remaining:', str(days_remaining)])
        
        # Create meta info table
        meta_table = Table(meta_data, colWidths=[3*cm, 10*cm])
        meta_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 11),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor('#666666')),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ]))
        
        story.append(meta_table)
        story.append(Spacer(1, 20))
        
        # Expiry warning if applicable
        if artifact.expiry_date:
            days_remaining = (artifact.expiry_date - datetime.now().date()).days
            if days_remaining < 0:
                story.append(Paragraph("⚠️ THIS ARTIFACT HAS EXPIRED", expired_style))
            elif days_remaining <= 7:
                story.append(Paragraph(f"⚠️ EXPIRES IN {days_remaining} DAYS", warning_style))
        
        # Content section
        if artifact.content:
            story.append(Paragraph("Content", heading_style))
            story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#bdc3c7')))
            story.append(Spacer(1, 15))
            
            # Process content
            cleaned_content = clean_markdown_for_pdf(artifact.content)
            
            # Split into paragraphs and add to story
            paragraphs = cleaned_content.split('\n')
            for para in paragraphs:
                para = para.strip()
                if para:
                    try:
                        story.append(Paragraph(para, content_style))
                    except:
                        # Fallback for problematic content
                        story.append(Paragraph(para.encode('ascii', 'ignore').decode('ascii'), content_style))

        # Images section
        if artifact.images:
            story.append(PageBreak())
            story.append(Paragraph("Images", heading_style))
            story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#bdc3c7')))
            story.append(Spacer(1, 15))
            
            for i, image_data in enumerate(artifact.images):
                # The path is already complete from the root directory
                # Remove 'static/' prefix if it exists since we need the file system path
                image_relative_path = image_data['path']
                if image_relative_path.startswith('static/'):
                    image_relative_path = image_relative_path[7:]  # Remove 'static/' prefix
                
                # Construct the full file system path
                image_path = os.path.join(os.path.dirname(__file__), 'static', image_relative_path)
                
                try:
                    # Check if image file exists
                    if not os.path.exists(image_path):
                        error_style = ParagraphStyle(
                            'ErrorStyle',
                            parent=styles['Normal'],
                            fontSize=10,
                            textColor=colors.HexColor('#e74c3c'),
                            alignment=TA_CENTER,
                            spaceAfter=15
                        )
                        story.append(Paragraph(f"Image not found: {image_data['name']} (Path: {image_path})", error_style))
                        continue
                    
                    # Open image with PIL to get dimensions
                    with PILImage.open(image_path) as pil_img:
                        img_width, img_height = pil_img.size
                        
                        # Calculate scaling to fit page width (max 15cm)
                        max_width = 15*cm
                        max_height = 10*cm
                        
                        # Calculate aspect ratio
                        aspect_ratio = img_width / img_height

                        if img_width > img_height:
                            # Landscape orientation
                            new_width = min(max_width, img_width * 72 / 96)  # Convert pixels to points
                            new_height = new_width / aspect_ratio
                        else:
                            # Portrait orientation
                            new_height = min(max_height, img_height * 72 / 96)
                            new_width = new_height * aspect_ratio
                        
                        # Ensure image doesn't exceed page dimensions
                        if new_width > max_width:
                            new_width = max_width
                            new_height = new_width / aspect_ratio
                        if new_height > max_height:
                            new_height = max_height
                            new_width = new_height * aspect_ratio
                    
                    # Create reportlab image
                    img = RLImage(image_path, width=new_width, height=new_height)
                    
                    # Center the image
                    img.hAlign = 'CENTER'
                    
                    story.append(img)
                    
                    # Add image caption
                    caption_style = ParagraphStyle(
                        'Caption',
                        parent=styles['Normal'],
                        fontSize=10,
                        textColor=colors.HexColor('#666666'),
                        alignment=TA_CENTER,
                        spaceAfter=20,
                        fontName='Helvetica-Oblique'
                    )
                    story.append(Paragraph(f"Figure {i+1}: {image_data['name']}", caption_style))
                    
                    if i < len(artifact.images) - 1:
                        story.append(Spacer(1, 20))

                except Exception as e:
                    # If image processing fails, add a note
                    error_style = ParagraphStyle(
                        'ErrorStyle',
                        parent=styles['Normal'],
                        fontSize=10,
                        textColor=colors.HexColor('#e74c3c'),
                        alignment=TA_CENTER,
                        spaceAfter=15
                    )
                    story.append(Paragraph(f"Could not load image: {image_data['name']} - {str(e)}", error_style))
        
        # Footer information
        story.append(PageBreak())
        footer_style = ParagraphStyle(
            'FooterStyle',
            parent=styles['Normal'],
            fontSize=10,
            textColor=colors.HexColor('#666666'),
            alignment=TA_CENTER,
            spaceAfter=10
        )
        
        story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#bdc3c7')))
        story.append(Spacer(1, 20))
        story.append(Paragraph("Generated by KeepStone", footer_style))
        story.append(Paragraph(f"Export Date: {datetime.now().strftime('%B %d, %Y at %I:%M %p')}", footer_style))
        
        # Build PDF
        doc.build(story)

        # Get PDF data
        pdf_data = buffer.getvalue()
        buffer.close()
        
        # Create response
        response = make_response(pdf_data)
        response.headers['Content-Type'] = 'application/pdf'
        
        # Clean filename for download
        safe_filename = re.sub(r'[^\w\s-]', '', artifact.name.strip())
        safe_filename = re.sub(r'[-\s]+', '_', safe_filename)
        
        response.headers['Content-Disposition'] = f'attachment; filename="{safe_filename}.pdf"'
        
        return response
        
    except Exception as e:
        app.logger.error(f"PDF export error: {str(e)}")
        flash(f'Error generating PDF: {str(e)}', 'error')
        return redirect(url_for('artifact_detail', artifact_id=artifact_id))

# Helper functions for project management
def get_default_project():
    """Get the default project (system-wide, regardless of user access)"""
    return session.query(Project).filter(Project.is_default == True).first()

def get_default_project_id():
    """Get the default project ID (system-wide, regardless of user access)"""
    default_project = get_default_project()
    return default_project.id if default_project else None

def get_user_default_project():
    """Get the current user's personal default project only if they have access to it"""
    if not current_user.is_authenticated:
        return None
    return current_user.get_default_project(session)

def get_user_default_project_id():
    """Get the current user's personal default project ID only if they have access to it"""
    user_default_project = get_user_default_project()
    return user_default_project.id if user_default_project else None

def get_user_accessible_projects():
    """Get projects accessible to the current user"""
    # All users (including admin) only see projects they're members of
    project_memberships = session.query(ProjectMember).filter_by(
        user_id=current_user.id,
        is_active=True
    ).all()
    
    project_ids = [m.project_id for m in project_memberships]
    if project_ids:
        return session.query(Project).filter(Project.id.in_(project_ids)).order_by(Project.name).all()
    else:
        return []

def get_user_accessible_project_ids():
    """Get project IDs accessible to the current user"""
    # All users (including admin) only see projects they're members of
    project_memberships = session.query(ProjectMember).filter_by(
        user_id=current_user.id,
        is_active=True
    ).all()
    return [m.project_id for m in project_memberships]

def user_has_project_access(project_id):
    """Check if current user has access to a specific project"""
    # For artifact access, admin still has full access for management purposes
    if current_user.is_admin:
        return True
    
    membership = session.query(ProjectMember).filter_by(
        user_id=current_user.id,
        project_id=project_id,
        is_active=True
    ).first()
    
    return membership is not None

def get_all_projects():
    """Get all projects accessible to the current user"""
    return get_user_accessible_projects()

# Project management routes
@app.route('/projects')
@login_required
@active_user_required
def projects():
    """List all projects accessible to the user"""
    # Get projects based on user role and permissions
    if current_user.is_admin:
        # Admin can see all projects
        projects = session.query(Project).order_by(Project.created_at.desc()).all()
        # Get project ownership and member info for each project
        project_data = []
        for project in projects:
            members = project.get_members(session)
            owner_membership = project.get_owner(session)
            
            # Get owner user object safely
            owner_user = None
            if owner_membership and owner_membership.user:
                owner_user = owner_membership.user
            
            project_info = {
                'project': project,
                'owner': owner_membership,
                'owner_user': owner_user,
                'member_count': len(members),
                'is_member': any(m.user_id == current_user.id for m in members),
                'is_owner': owner_membership and owner_membership.user_id == current_user.id
            }
            project_data.append(project_info)
    else:
        # Regular user sees only projects they're a member of
        project_memberships = session.query(ProjectMember).filter_by(
            user_id=current_user.id,
            is_active=True
        ).all()
        
        project_data = []
        for membership in project_memberships:
            project = membership.project
            members = project.get_members(session)
            owner_membership = project.get_owner(session)
            
            # Get owner user object safely
            owner_user = None
            if owner_membership and owner_membership.user:
                owner_user = owner_membership.user
            
            project_info = {
                'project': project,
                'owner': owner_membership,
                'owner_user': owner_user,
                'member_count': len(members),
                'is_member': True,
                'is_owner': membership.role == 'owner',
                'role': membership.role
            }
            project_data.append(project_info)
    
    default_project = get_default_project()
    
    # Get artifact counts for each project the user can access
    project_artifacts = {}
    for item in project_data:
        project = item['project']
        count = session.query(Artifact).filter(
            Artifact.project_id == project.id,
            Artifact.deleted == False
        ).count()
        project_artifacts[project.id] = count
    
    return render_template('projects.html', 
                         project_data=project_data,
                         default_project=default_project,
                         user_default_project=get_user_default_project(),
                         project_artifacts=project_artifacts,
                         is_admin=current_user.is_admin)

@app.route('/projects/add', methods=['GET', 'POST'])
@login_required
@active_user_required
def add_project():
    """Add a new project"""
    if request.method == 'GET':
        return render_template('add_project.html')
    
    try:
        name = request.form['name'].strip()
        description = request.form.get('description', '').strip()
        
        if not name:
            flash('Project name is required', 'error')
            return render_template('add_project.html')
        
        # Check if project already exists
        existing = session.query(Project).filter(Project.name == name).first()
        if existing:
            flash('Project with this name already exists', 'error')
            return render_template('add_project.html')
        
        # Create project with creator
        project = Project(
            name=name, 
            description=description,
            created_by=current_user.id
        )
        session.add(project)
        session.flush()  # Get the project ID
        
        # Add creator as owner
        project.add_member(session, current_user.id, role='owner', added_by=current_user.id)
        
        session.commit()
        
        # Initialize project configurations with default values (including project types)
        initialize_project_configs(project.id)
        
        flash(f'Project "{name}" created successfully!', 'success')
        return redirect(url_for('projects'))
    except Exception as e:
        flash(f'Error creating project: {str(e)}', 'error')
        session.rollback()
        return render_template('add_project.html')

@app.route('/projects/<int:project_id>/set_default', methods=['POST'])
@login_required
@active_user_required
def set_default_project(project_id):
    """Set a project as the user's personal default project"""
    try:
        project = session.query(Project).get(project_id)
        if not project:
            flash('Project not found', 'error')
            return redirect(url_for('projects'))
        
        # Set this project as the user's personal default
        if current_user.set_default_project(project_id, session):
            session.commit()
            flash(f'"{project.name}" set as your personal default project', 'success')
        else:
            flash('You do not have access to set this project as default', 'error')
    except Exception as e:
        flash(f'Error setting default project: {str(e)}', 'error')
        session.rollback()
    
    return redirect(url_for('projects'))

@app.route('/projects/clear_default', methods=['POST'])
@login_required
@active_user_required
def clear_default_project():
    """Clear the user's personal default project"""
    try:
        current_user.set_default_project(None, session)
        session.commit()
        flash('Personal default project cleared', 'info')
    except Exception as e:
        flash(f'Error clearing default project: {str(e)}', 'error')
        session.rollback()
    
    return redirect(url_for('projects'))

@app.route('/projects/<int:project_id>/delete', methods=['POST'])
@login_required
@active_user_required
def delete_project(project_id):
    """Delete a project"""
    try:
        project = session.query(Project).get(project_id)
        if not project:
            flash('Project not found', 'error')
            return redirect(url_for('projects'))
        
        # Check if there's only one project left
        total_projects = session.query(Project).count()
        if total_projects <= 1:
            flash('Cannot delete the last remaining project. At least one project must exist.', 'error')
            return redirect(url_for('projects'))
        
        if project.is_default:
            flash('Cannot delete the default project. Set another project as default first.', 'error')
            return redirect(url_for('projects'))
        
        # Check if project has artifacts
        artifact_count = session.query(Artifact).filter(Artifact.project_id == project_id).count()
        if artifact_count > 0:
            flash(f'Cannot delete project with {artifact_count} artifacts. Move or delete them first.', 'error')
            return redirect(url_for('projects'))
        
        project_name = project.name
        session.delete(project)
        session.commit()
        flash(f'Project "{project_name}" deleted successfully', 'success')
    except Exception as e:
        flash(f'Error deleting project: {str(e)}', 'error')
        session.rollback()
    
    return redirect(url_for('projects'))

@app.route('/projects/<int:project_id>/edit', methods=['GET', 'POST'])
@login_required
@active_user_required
def edit_project(project_id):
    """Edit a project"""
    print(f"EDIT_PROJECT: Route called with method {request.method} for project {project_id}")
    
    project = session.query(Project).get(project_id)
    if not project:
        flash('Project not found', 'error')
        return redirect(url_for('projects'))
    
    # Check if user has access to this project
    if not user_has_project_access(project_id):
        flash('You do not have permission to edit this project', 'error')
        return redirect(url_for('projects'))
    
    if request.method == 'GET':
        print(f"EDIT_PROJECT: Serving GET request for project {project.name}")
        # Get projects list and artifact count for the template
        projects = get_all_projects()
        artifact_count = session.query(Artifact).filter(
            Artifact.project_id == project_id,
            Artifact.deleted == False
        ).count()
        project_artifacts = {project_id: artifact_count}
        
        return render_template('edit_project.html', 
                             project=project, 
                             projects=projects,
                             project_artifacts=project_artifacts)
    
    # Handle POST request
    print(f"EDIT_PROJECT: Processing POST request with form data: {dict(request.form)}")
    try:
        name = request.form.get('name', '').strip()
        description = request.form.get('description', '').strip()
        
        print(f"EDIT_PROJECT: Extracted name='{name}', description='{description}'")
        
        if not name:
            flash('Project name is required', 'error')
            # Get projects list and artifact count for the template
            projects = get_all_projects()
            artifact_count = session.query(Artifact).filter(
                Artifact.project_id == project_id,
                Artifact.deleted == False
            ).count()
            project_artifacts = {project_id: artifact_count}
            return render_template('edit_project.html', 
                                 project=project, 
                                 projects=projects,
                                 project_artifacts=project_artifacts)
        
        # Check if another project with the same name exists
        existing = session.query(Project).filter(
            Project.name == name, 
            Project.id != project_id
        ).first()
        if existing:
            flash('Another project with this name already exists', 'error')
            # Get projects list and artifact count for the template
            projects = get_all_projects()
            artifact_count = session.query(Artifact).filter(
                Artifact.project_id == project_id,
                Artifact.deleted == False
            ).count()
            project_artifacts = {project_id: artifact_count}
            return render_template('edit_project.html', 
                                 project=project, 
                                 projects=projects,
                                 project_artifacts=project_artifacts)
        
        # Update project
        project.name = name
        project.description = description if description else None
        
        # Ensure we have a fresh session and commit properly
        session.flush()  # Flush changes to database
        session.commit()  # Commit the transaction
        session.refresh(project)  # Refresh the object from the database
        
        flash(f'Project "{name}" updated successfully!', 'success')
        return redirect(url_for('projects'))
        
    except Exception as e:
        session.rollback()
        flash(f'Error updating project: {str(e)}', 'error')
        # Get projects list and artifact count for the template
        projects = get_all_projects()
        artifact_count = session.query(Artifact).filter(
            Artifact.project_id == project_id,
            Artifact.deleted == False
        ).count()
        project_artifacts = {project_id: artifact_count}
        return render_template('edit_project.html', 
                             project=project, 
                             projects=projects,
                             project_artifacts=project_artifacts)

@app.route('/projects/<int:project_id>/move_artifacts', methods=['POST'])
@login_required
@active_user_required
def move_artifacts(project_id):
    """Move all artifacts from one project to another"""
    try:
        source_project = session.query(Project).get(project_id)
        target_project_id = request.form.get('target_project_id')
        
        if not source_project:
            flash('Source project not found', 'error')
            return redirect(url_for('projects'))
        
        if not target_project_id:
            flash('Target project not specified', 'error')
            return redirect(url_for('projects'))
        
        target_project = session.query(Project).get(target_project_id)
        if not target_project:
            flash('Target project not found', 'error')
            return redirect(url_for('projects'))
        
        # Move all artifacts from source to target
        artifacts = session.query(Artifact).filter(Artifact.project_id == project_id).all()
        for artifact in artifacts:
            artifact.project_id = target_project_id
        
        session.commit()
        flash(f'Moved {len(artifacts)} artifacts from "{source_project.name}" to "{target_project.name}"', 'success')
    except Exception as e:
        flash(f'Error moving artifacts: {str(e)}', 'error')
        session.rollback()
    
    return redirect(url_for('projects'))

# Project Member Management Routes
@app.route('/projects/<int:project_id>/members')
@login_required
@active_user_required
def project_members(project_id):
    """Manage project members"""
    project = session.query(Project).get(project_id)
    if not project:
        flash('Project not found.', 'error')
        return redirect(url_for('projects'))
    
    # Check if user has access to this project
    user_membership = session.query(ProjectMember).filter_by(
        project_id=project_id,
        user_id=current_user.id,
        is_active=True
    ).first()
    
    if not current_user.is_admin and not user_membership:
        flash('You do not have access to this project.', 'error')
        return redirect(url_for('projects'))
    
    # Get project members
    members = project.get_members(session)
    member_data = []
    for member in members:
        member_info = {
            'membership': member,
            'user': member.user,
            'added_by': member.added_by_user,
            'can_remove': (
                current_user.is_admin or 
                user_membership and user_membership.role == 'owner' or
                member.user_id == current_user.id
            )
        }
        member_data.append(member_info)
    
    # Get all users for adding new members (excluding current members)
    current_member_ids = [m.user_id for m in members]
    available_users = session.query(User).filter(
        User.is_active == True,
        ~User.id.in_(current_member_ids)
    ).order_by(User.full_name).all()
    
    is_owner = user_membership and user_membership.role == 'owner'
    
    return render_template('project_members.html',
                         project=project,
                         member_data=member_data,
                         available_users=available_users,
                         is_owner=is_owner,
                         is_admin=current_user.is_admin)

@app.route('/projects/<int:project_id>/members/add', methods=['POST'])
@login_required
@active_user_required
def add_project_member(project_id):
    """Add a user to a project"""
    project = session.query(Project).get(project_id)
    if not project:
        flash('Project not found.', 'error')
        return redirect(url_for('projects'))
    
    # Check permissions - only owner, admin, or existing members can add
    user_membership = session.query(ProjectMember).filter_by(
        project_id=project_id,
        user_id=current_user.id,
        is_active=True
    ).first()
    
    if not current_user.is_admin and not user_membership:
        flash('You do not have permission to add members to this project.', 'error')
        return redirect(url_for('project_members', project_id=project_id))
    
    user_id = request.form.get('user_id')
    role = request.form.get('role', 'member')
    
    if not user_id:
        flash('Please select a user to add.', 'error')
        return redirect(url_for('project_members', project_id=project_id))
    
    # Validate role permissions
    if role == 'owner' and not (current_user.is_admin or (user_membership and user_membership.role == 'owner')):
        flash('You do not have permission to assign owner role.', 'error')
        return redirect(url_for('project_members', project_id=project_id))
    
    try:
        # Add the member
        project.add_member(session, int(user_id), role=role, added_by=current_user.id)
        session.commit()
        
        user = session.query(User).get(user_id)
        flash(f'Successfully added {user.full_name} to the project!', 'success')
        
    except Exception as e:
        session.rollback()
        flash(f'Error adding member: {str(e)}', 'error')
    
    return redirect(url_for('project_members', project_id=project_id))

@app.route('/projects/<int:project_id>/members/<int:user_id>/remove', methods=['POST'])
@login_required
@active_user_required
def remove_project_member(project_id, user_id):
    """Remove a user from a project"""
    project = session.query(Project).get(project_id)
    if not project:
        flash('Project not found.', 'error')
        return redirect(url_for('projects'))
    
    # Check permissions
    user_membership = session.query(ProjectMember).filter_by(
        project_id=project_id,
        user_id=current_user.id,
        is_active=True
    ).first()
    
    if not current_user.is_admin and not (user_membership and user_membership.role == 'owner') and user_id != current_user.id:
        flash('You do not have permission to remove this member.', 'error')
        return redirect(url_for('project_members', project_id=project_id))
    
    try:
        # Remove the member
        project.remove_member(session, user_id)
        session.commit()
        
        user = session.query(User).get(user_id)
        if user_id == current_user.id:
            flash('You have left the project.', 'info')
            return redirect(url_for('projects'))
        else:
            flash(f'Successfully removed {user.full_name} from the project.', 'success')
        
    except Exception as e:
        session.rollback()
        flash(f'Error removing member: {str(e)}', 'error')
    
    return redirect(url_for('project_members', project_id=project_id))

# Project Settings Routes
@app.route('/projects/<int:project_id>/settings', methods=['GET', 'POST'])
@login_required
@active_user_required
def project_settings(project_id):
    """Project-specific settings page"""
    from utils.project_config_utils import (
        get_project_configs_for_settings, 
        update_project_config, 
        initialize_project_configs,
        get_project_level_config_keys
    )
    
    # Check if user has access to this project
    project = session.query(Project).get(project_id)
    if not project:
        flash('Project not found.', 'error')
        return redirect(url_for('projects'))
    
    # Check permissions - only admin or project members can access settings
    if not current_user.is_admin:
        membership = project.get_user_membership(session, current_user.id)
        if not membership or membership.role not in ['owner', 'admin']:
            flash('You do not have permission to access project settings.', 'error')
            return redirect(url_for('projects'))
    
    if request.method == 'POST':
        try:
            # Get project-level config keys
            project_keys = get_project_level_config_keys()
            
            # Get all form data
            updates = {}
            for key in request.form:
                if key in project_keys:
                    value = request.form[key]
                    
                    # Convert values to appropriate types
                    if key == 'type':
                        # Handle arrays
                        value = [t.strip() for t in value.split(',') if t.strip()]
                    elif value.lower() in ('true', 'false'):
                        value = value.lower() == 'true'
                    
                    updates[key] = value
            
            # Update each config item
            success_count = 0
            for key, value in updates.items():
                if update_project_config(project_id, key, value):
                    success_count += 1
            
            if success_count > 0:
                flash(f'Successfully updated {success_count} project configuration(s)!', 'success')
            else:
                flash('No configurations were updated.', 'error')
                
        except Exception as e:      
            flash(f'Error updating project configuration: {str(e)}', 'error')
        
        return redirect(url_for('project_settings', project_id=project_id))
    
    # Initialize project configs if they don't exist
    initialize_project_configs(project_id)
    
    # Get all config items for display
    config_items = get_project_configs_for_settings(project_id)
    
    return render_template('project_settings.html', 
                         project=project, 
                         config_items=config_items)

# All routes are defined above. The following runs the app if executed directly.

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=2222, debug=True)