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
utility.create_database(config=config)
Session = sessionmaker(bind=models.base.engine)
session = Session()
Artifact = models.artifact.Artifact
Type = models.type.Type

# Make date available in templates
@app.context_processor
def inject_date():
    return dict(date=date)


# Create markdown renderer
markdowner = Markdown(extras=["tables", "fenced-code-blocks"])

@app.template_filter('markdown')
def markdown_filter(text):
    return markdowner.convert(text)

@app.route('/')
def index():
    search_query = request.args.get('search', '')
    type_filter = request.args.get('type', '')
    
    # Start with base query
    query = session.query(Artifact)
    
    # Apply search filter if present
    if search_query:
        name_results = query.filter(Artifact.name.ilike(f'%{search_query}%'))
        content_results = query.filter(Artifact.content.ilike(f'%{search_query}%'))
        query = name_results.union(content_results)
    
    # Apply type filter if present
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
                         types_dict=types_dict,
                         config=config)

@app.route('/add', methods=['GET', 'POST'])
def add_artifact():
    if request.method == 'POST':
        name = request.form['name']
        type_id = request.form['artifact_type']
        content = request.form['content']
        expiry_date_str = request.form['expiry_date']
        
        try:
            expiry_date = datetime.strptime(expiry_date_str, '%Y-%m-%d').date()
            
            # Handle multiple image uploads
            images_data = []
            if 'images[]' in request.files:
                files = request.files.getlist('images[]')
                for file in files:
                    if file and file.filename:
                        image_name = secure_filename(file.filename)
                        image_data = base64.b64encode(file.read()).decode('utf-8')
                        images_data.append({
                            'name': image_name,
                            'data': image_data
                        })
            
            artifact = Artifact(
                name=name,
                content=content,
                expiry_date=expiry_date,
                type_id=type_id,
                images=images_data
            )
            
            session.add(artifact)
            session.commit()
            
            flash('Artifact added successfully!', 'success')
            return redirect(url_for('index'))
            
        except ValueError:
            flash('Invalid date format. Please use YYYY-MM-DD.', 'error')
        except Exception as e:
            flash(f'Error: {str(e)}', 'error')

    types = session.query(Type).all()
    return render_template('add_artifact.html', types=types)

@app.route('/delete/<int:artifact_id>', methods=['POST'])
def delete_artifact(artifact_id):
    artifact = session.query(Artifact).filter(Artifact.id==artifact_id).first()
    session.delete(artifact)
    session.commit()
    flash('Artifact deleted successfully!', 'success')
    return redirect(url_for('index'))

@app.route('/update/<int:artifact_id>', methods=['GET', 'POST'])
def update_artifact(artifact_id):
    artifact = session.query(Artifact).filter(Artifact.id==artifact_id).first()
    if request.method == 'POST':
        try:
            artifact.name = request.form['name']
            artifact.content = request.form['content']
            artifact.type_id = request.form['artifact_type']
            expiry_date = datetime.strptime(request.form['expiry_date'], '%Y-%m-%d').date()
            artifact.expiry_date = expiry_date

            # Handle removed images
            removed_images = request.form.get('removed_images', '').split(',')
            if artifact.images:
                artifact.images = [img for img in artifact.images if img['name'] not in removed_images]

            # Handle new images
            if 'images[]' in request.files:
                files = request.files.getlist('images[]')
                for file in files:
                    if file and file.filename:
                        image_name = secure_filename(file.filename)
                        image_data = base64.b64encode(file.read()).decode('utf-8')
                        if not artifact.images:
                            artifact.images = []
                        artifact.images.append({
                            'name': image_name,
                            'data': image_data
                        })

            session.commit()
            flash('Artifact updated successfully!', 'success')
            return redirect(url_for('index'))
            
        except ValueError:
            flash('Invalid date format. Please use YYYY-MM-DD.', 'error')
        except Exception as e:
            flash(f'Error updating artifact: {str(e)}', 'error')

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
                         status_icon=status_icon)

# All routes are defined above. The following runs the app if executed directly.
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=2222, debug=True)