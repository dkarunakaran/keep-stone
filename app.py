from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, date
import os
import utility
import yaml
from sqlalchemy.orm import sessionmaker
import base64
from werkzeug.utils import secure_filename
from markdown2 import Markdown
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
import pytz
from email_utils import check_expiring_tokens
from flask import send_from_directory
import atexit
from utility import save_image, delete_image
import sys
parent_dir = ".."
sys.path.append(parent_dir)
import models.base
import models.artifact
import models.type

# Fix for template rendering
import sys
sys.path.append('/app')

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here'

# Create instance directory if it doesn't exist
instance_path = '/app/instance'
os.makedirs(instance_path, exist_ok=True)

with open("config.yaml") as f:
    config = yaml.load(f, Loader=yaml.FullLoader)

# Create database if it doesn't exist
utility.create_database(config=config)
Session = sessionmaker(bind=models.base.engine)
session = Session()
Artifact = models.artifact.Artifact
Type = models.type.Type

# Make date available in templates
@app.context_processor
def inject_date():
    return dict(date=date)

@app.context_processor
def utility_processor():
    return dict(timezone=pytz.timezone)

# Create markdown renderer
markdowner = Markdown(extras=["tables", "fenced-code-blocks"])

@app.template_filter('markdown')
def markdown_filter(text):
    return markdowner.convert(text)

# Setup scheduler for token expiry checks
scheduler = BackgroundScheduler()
scheduler.add_job(
    func=lambda: check_expiring_tokens(session, config),
    trigger=CronTrigger(
        hour=config['email']['trigger_hour'], 
        minute=config['email']['trigger_minute'],
        timezone=pytz.timezone(config['email']['timezone'])  # AEST timezone
    ),
    misfire_grace_time=3600  # Allow job to run up to 1 hour late if needed
)
scheduler.start()

# Shutdown scheduler when app stops
atexit.register(lambda: scheduler.shutdown())

@app.route('/')
def index():
    search_query = request.args.get('search', '')
    type_filter = request.args.get('type', '')  # Changed to empty string default
    
    # Start with base query
    query = session.query(Artifact)
    
    # Apply search filter if present
    if search_query:
        name_results = query.filter(Artifact.name.ilike(f'%{search_query}%'))
        content_results = query.filter(Artifact.content.ilike(f'%{search_query}%'))
        query = name_results.union(content_results)
    
    # Apply type filter only if specifically selected
    if type_filter:
        query = query.filter(Artifact.type_id == type_filter)
    
    # Get final results
    artifacts = query.order_by(Artifact.expiry_date.asc()).all()
    
    # Get types for dropdown
    types = session.query(Type).all()
    types_dict = {t.id: t.name for t in types}
    
    return render_template('index.html', 
                         artifacts=artifacts,
                         search_query=search_query,
                         type_filter=type_filter,
                         today=date.today(),
                         types=types,
                         config=config,
                         types_dict=types_dict)


@app.route('/add', methods=['GET', 'POST'])
def add_artifact():
    if request.method == 'POST':
        try:
            # Get form data
            name = request.form['name']
            type_id = request.form['artifact_type']
            content = request.form['content']
            expiry_date_str = request.form.get('expiry_date')
            
            # Handle expiry date
            expiry_date = None
            if expiry_date_str:
                expiry_date = datetime.strptime(expiry_date_str, '%Y-%m-%d').date()
            
            # Handle image uploads
            files = request.files.getlist('images[]')
            images_data = []
            
            for file in files:
                if file and file.filename:
                    if not file.content_type.startswith('image/'):
                        raise ValueError(f"Invalid file type: {file.filename}")
                    
                    if file.content_length > config['storage']['max_file_size']:
                        raise ValueError(f"File too large: {file.filename}")
                    
                    # Save image and store metadata
                    relative_path = save_image(file, config)
                    images_data.append({
                        'name': file.filename,
                        'path': relative_path
                    })
            
            # Create artifact with image metadata
            artifact = Artifact(
                name=request.form['name'],
                type_id=request.form['artifact_type'],
                content=request.form['content'],
                expiry_date=expiry_date,
                images=images_data
            )
            
            session.add(artifact)
            session.commit()
            
            flash('Artifact created successfully!', 'success')
            return redirect(url_for('index'))
            
        except Exception as e:
            # Delete any saved images if artifact creation fails
            for image in images_data:
                delete_image(image['path'])
            flash(str(e), 'error')
            session.rollback()
    
    # GET request - show form
    types = session.query(Type).all()
    return render_template('add_artifact.html', types=types)

@app.route('/delete/<int:artifact_id>', methods=['POST'])
def delete_artifact(artifact_id):
    artifact = session.query(Artifact).get(artifact_id)
    if artifact:
        # Delete associated images
        for image in artifact.images:
            delete_image(image['path'])
        
        session.delete(artifact)
        session.commit()
    return redirect(url_for('index'))

@app.route('/update/<int:artifact_id>', methods=['GET', 'POST'])
def update_artifact(artifact_id):
    artifact = session.query(Artifact).filter(Artifact.id==artifact_id).first()
    if request.method == 'POST':
        try:
            # Update basic info
            artifact.name = request.form['name']
            artifact.content = request.form['content']
            artifact.type_id = request.form['artifact_type']
            
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
            removed_images = request.form.get('removed_images', '').split(',')
            if removed_images[0]:
                for img in artifact.images[:]:
                    if img['name'] in removed_images:
                        delete_image(img['path'])
                        artifact.images.remove(img)

            # Handle new images
            files = request.files.getlist('images[]')
            for file in files:
                if file and file.filename:
                    if not file.content_type.startswith('image/'):
                        raise ValueError(f"Invalid file type: {file.filename}")
                    
                    if file.content_length > config['storage']['max_file_size']:
                        raise ValueError(f"File too large: {file.filename}")
                    
                    # Save new image
                    relative_path = save_image(file, config)
                    artifact.images.append({
                        'name': file.filename,
                        'path': relative_path
                    })
            
            session.add(artifact)
            session.commit()
            
            flash('Artifact updated successfully!', 'success')
            return redirect(url_for('index'))
            
        except Exception as e:
            flash(str(e), 'error')
            session.rollback()

    types = session.query(Type).all()
    return render_template('update_artifact.html', artifact=artifact, types=types)

@app.route('/artifact/<int:artifact_id>')
def artifact_detail(artifact_id):
    artifact = session.query(Artifact).filter(Artifact.id==artifact_id).first()
    if not artifact:
        flash('Artifact not found!', 'error')
        return redirect(url_for('index'))
    
    # Get type name
    type_obj = session.query(Type).filter(Type.id==artifact.type_id).first()
    type_name = type_obj.name if type_obj else 'Unknown'
    
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
                         config=config)


@app.route('/static/uploads/<path:filename>')
def serve_image(filename):
    return send_from_directory(config['storage']['image_path'], filename)

# All routes are defined above. The following runs the app if executed directly.
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=2222, debug=True)