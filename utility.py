from sqlalchemy.orm import sessionmaker
from sqlalchemy import and_
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
import models.type
import models.config
import models.project
import models.user

def create_database(session=None, config=None):
    """
    Create the database and tables if they do not exist.
    """
    if session is None:
        Session = sessionmaker(bind=models.base.engine)
        session = Session()
    
    models.base.Base.metadata.create_all(models.base.engine)

    Type = models.type.Type

    # Insert Groups
    all_types= session.query(Type).all()
    if len(all_types) < 1 and config:
        types = config.get('type', [])
            
        for name in types:
            # Create a new group object
            type = Type(name=name)
            # Add the new group to the session
            session.add(type)
            # Commit the changes to the database
            session.commit() 

    initialize_config_table()

    # Close the session if it was created here
    if session is not None:
        session.close()

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


