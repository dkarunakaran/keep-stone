import logging
import yaml
import sys
import os
from sqlalchemy.orm import sessionmaker
from datetime import datetime, date
from models.base import engine
from models.artifact import Artifact
from utility import delete_image
from email_utils import check_expiring_tokens

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)
Session = sessionmaker(bind=engine)

# Load configuration
with open('/app/config.yaml', 'r') as f:
    config = yaml.safe_load(f)

def cleanup_deleted_artifacts(session):
    """Delete artifacts that were soft-deleted"""
    try:
        # Create database session
        session = Session()

        # Find artifacts ready for cleanup
        artifacts_to_delete = session.query(Artifact)\
            .filter(Artifact.deleted == True)\
            .all()

        deleted_count = 0
        for artifact in artifacts_to_delete:
            if artifact.is_ready_for_cleanup(config):
                # Delete associated images
                if artifact.images:
                    for image in artifact.images:
                        delete_image(image['path'])
                
                # Permanently delete the artifact
                session.delete(artifact)
                deleted_count += 1

        if deleted_count > 0:
            session.commit()
            logger.info(f"Permanently deleted {deleted_count} artifacts")

    except Exception as e:
        logger.error(f"Error during cleanup: {str(e)}")
        session.rollback()

def run_scheduler():
    try:
        
        # Create database session
        session = Session()
        
        try:
            # Check expiring tokens
            check_expiring_tokens(session, config)
            logger.info("Token check completed")

            # Clean up deleted artifacts
            cleanup_deleted_artifacts(session)
            logger.info("Cleanup check completed")
        except Exception as e:
            logger.error(f"Error running scheduled tasks: {str(e)}")
        finally:
            session.close()
            
    except Exception as e:
        logger.error(f"Error in scheduler setup: {str(e)}")
        if 'session' in locals():
            session.close()
        sys.exit(1)

if __name__ == "__main__":
    run_scheduler()