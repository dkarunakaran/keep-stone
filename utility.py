from sqlalchemy.orm import sessionmaker
from sqlalchemy import and_

import sys
parent_dir = ".."
sys.path.append(parent_dir)
# Need to import all model files to create table
import models.artifact
import models.base
import models.type

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
    if len(all_types) < 1:
        types = config['type']
            
        for name in types:
            # Create a new group object
            type = Type(name=name)
            # Add the new group to the session
            session.add(type)
            # Commit the changes to the database
            session.commit() 
    
    # Close the session if it was created here
    if session is not None:
        session.close()




