from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, date
import os
import utility
import yaml
from sqlalchemy.orm import sessionmaker

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

@app.route('/')
def index():
    search_query = request.args.get('search', '')
    if search_query:
        # Search in name
        name_results = session.query(Artifact).filter(
            Artifact.name.ilike(f'%{search_query}%')
        )
        
        # Search in used_for
        used_for_results = Artifact.query.filter(
            Artifact.used_for.ilike(f'%{search_query}%')
        )
        
        # Combine results using union and order them
        artifacts = name_results.union(used_for_results).order_by(Artifact.expiry_date.asc()).all()
    else:
        artifacts = session.query(Artifact).order_by(Artifact.expiry_date.asc()).all()
    
    types = session.query(Type).all()
    types_dict = {t.id: t.name for t in types}
    print(config)
    
    return render_template('index.html', artifacts=artifacts, search_query=search_query, today=date.today(), types_dict=types_dict, config=config)

@app.route('/add', methods=['GET', 'POST'])
def add_artifact():
    if request.method == 'POST':
        name = request.form['name']
        type_id = request.form['artifact_type']
        used_for = request.form['used_for']
        expiry_date_str = request.form['expiry_date']
        
        try:
            expiry_date = datetime.strptime(expiry_date_str, '%Y-%m-%d').date()
            
            artifact = Artifact(
                name=name,
                used_for=used_for,
                expiry_date=expiry_date,
                type_id=type_id  
            )
            
            session.add(artifact)
            session.commit()
            
            flash('Artifact added successfully!', 'success')
            return redirect(url_for('index'))
            
        except ValueError:
            flash('Invalid date format. Please use YYYY-MM-DD.', 'error')

    # Fetch types from database
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
            artifact.used_for = request.form['used_for']
            artifact.type_id = request.form['artifact_type']
            expiry_date = datetime.strptime(request.form['expiry_date'], '%Y-%m-%d').date()
            artifact.expiry_date = expiry_date
            session.commit()
            flash('Artifact updated successfully!', 'success')
            return redirect(url_for('index'))
            
        except ValueError:
            flash('Invalid date format. Please use YYYY-MM-DD.', 'error')

    # Fetch types from database
    types = session.query(Type).all()
            
    return render_template('update_artifact.html', artifact=artifact, types=types)

'''
@app.route('/api/artifacts')
def api_artifacts():
    artifacts = Artifact.query.all()
    return jsonify([artifact.to_dict() for artifact in artifacts])'''

# Add after existing routes, before if __name__ == '__main__':

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=2222, debug=True)