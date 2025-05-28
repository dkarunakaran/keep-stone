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

# Fix for template rendering
import sys
sys.path.append('/app')

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here'

# Create instance directory if it doesn't exist
instance_path = '/app/instance'
os.makedirs(instance_path, exist_ok=True)

app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{instance_path}/data.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

'''
with open("config.yaml") as f:
    config = yaml.load(f, Loader=yaml.FullLoader)
utility.create_database(config=config)
Session = sessionmaker(bind=models.base.engine)
session = Session()'''

# Make date available in templates
@app.context_processor
def inject_date():
    return dict(date=date)

# Artifact Model
class Artifact(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    used_for = db.Column(db.String(200), nullable=False)
    expiry_date = db.Column(db.Date, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    '''def is_expired(self):
        return self.expiry_date < date.today()
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'used_for': self.used_for,
            'expiry_date': self.expiry_date.strftime('%Y-%m-%d'),
            'is_expired': self.is_expired(),
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S')
        }'''

# Create tables
with app.app_context():
    db.create_all()

@app.route('/')
def index():
    search_query = request.args.get('search', '')
    
    '''if search_query:
        artifacts = Artifact.query.filter(
            db.or_(
                Artifact.name.ilike(f'%{search_query}%'),
                Artifact.used_for.ilike(f'%{search_query}%')
            )
        ).order_by(Artifact.expiry_date.asc()).all()
    else:
        artifacts = Artifact.query.order_by(Artifact.expiry_date.asc()).all()'''
    if search_query:
        # Search in name
        name_results = Artifact.query.filter(
            Artifact.name.ilike(f'%{search_query}%')
        )
        
        # Search in used_for
        used_for_results = Artifact.query.filter(
            Artifact.used_for.ilike(f'%{search_query}%')
        )
        
        # Combine results using union and order them
        artifacts = name_results.union(used_for_results).order_by(Artifact.expiry_date.asc()).all()
    else:
        artifacts = Artifact.query.order_by(Artifact.expiry_date.asc()).all()
    
    return render_template('index.html', artifacts=artifacts, search_query=search_query, today=date.today())

@app.route('/add', methods=['GET', 'POST'])
def add_artifact():
    if request.method == 'POST':
        name = request.form['name']
        used_for = request.form['used_for']
        expiry_date_str = request.form['expiry_date']
        
        try:
            expiry_date = datetime.strptime(expiry_date_str, '%Y-%m-%d').date()
            
            artifact = Artifact(
                name=name,
                used_for=used_for,
                expiry_date=expiry_date
            )
            
            db.session.add(artifact)
            db.session.commit()
            
            flash('Artifact added successfully!', 'success')
            return redirect(url_for('index'))
            
        except ValueError:
            flash('Invalid date format. Please use YYYY-MM-DD.', 'error')
    
    return render_template('add_artifact.html')

@app.route('/delete/<int:artifact_id>', methods=['POST'])
def delete_artifact(artifact_id):
    artifact = Artifact.query.get_or_404(artifact_id)
    db.session.delete(artifact)
    db.session.commit()
    flash('Artifact deleted successfully!', 'success')
    return redirect(url_for('index'))

@app.route('/update/<int:artifact_id>', methods=['GET', 'POST'])
def update_artifact(artifact_id):
    artifact = Artifact.query.get_or_404(artifact_id)
    
    if request.method == 'POST':
        try:
            artifact.name = request.form['name']
            artifact.used_for = request.form['used_for']
            expiry_date = datetime.strptime(request.form['expiry_date'], '%Y-%m-%d').date()
            artifact.expiry_date = expiry_date
            
            db.session.commit()
            flash('Artifact updated successfully!', 'success')
            return redirect(url_for('index'))
            
        except ValueError:
            flash('Invalid date format. Please use YYYY-MM-DD.', 'error')
            
    return render_template('update_artifact.html', artifact=artifact)

'''
@app.route('/api/artifacts')
def api_artifacts():
    artifacts = Artifact.query.all()
    return jsonify([artifact.to_dict() for artifact in artifacts])'''

# Add after existing routes, before if __name__ == '__main__':

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=2222, debug=True)