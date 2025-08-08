import logging
import yaml
import sys
import os
import shutil
import glob
from sqlalchemy.orm import sessionmaker
from datetime import datetime, date, timedelta
from models.base import engine
from models.artifact import Artifact
from models.project import Project  # Import Project model to register the table
from utility import delete_image
from utils.email_utils import check_expiring_tokens
from utils.config_utils import load_config

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

# Load config from database instead of YAML
config = load_config()

def cleanup_deleted_artifacts(session):
    """Delete artifacts that were soft-deleted"""
    try:
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

def get_last_backup_date():
    """Get the date of the last backup from a marker file"""
    backup_marker_file = "/tmp/keepstone_last_backup"
    try:
        if os.path.exists(backup_marker_file):
            with open(backup_marker_file, 'r') as f:
                date_str = f.read().strip()
                return datetime.strptime(date_str, '%Y-%m-%d').date()
    except Exception as e:
        logger.warning(f"Could not read last backup date: {str(e)}")
    return None

def set_last_backup_date(backup_date):
    """Set the date of the last backup in a marker file"""
    backup_marker_file = "/tmp/keepstone_last_backup"
    try:
        with open(backup_marker_file, 'w') as f:
            f.write(backup_date.strftime('%Y-%m-%d'))
    except Exception as e:
        logger.error(f"Could not write last backup date: {str(e)}")

def should_run_backup(config):
    """Check if backup should run based on configuration and last backup date"""
    if not config.get('backup', {}).get('enabled', False):
        return False
    
    last_backup = get_last_backup_date()
    today = date.today()
    backup_day = config.get('backup', {}).get('backup_day', 'sunday').lower()
    
    # Map day names to weekday numbers (Monday=0, Sunday=6)
    day_mapping = {
        'monday': 0, 'tuesday': 1, 'wednesday': 2, 'thursday': 3,
        'friday': 4, 'saturday': 5, 'sunday': 6
    }
    
    target_weekday = day_mapping.get(backup_day, 6)  # Default to Sunday
    
    # Check if today is the backup day
    if today.weekday() != target_weekday:
        return False
    
    # If no previous backup, run it
    if last_backup is None:
        return True
    
    # Check if at least 7 days have passed since last backup
    days_since_backup = (today - last_backup).days
    return days_since_backup >= 7

def cleanup_old_backups(backup_path, keep_count):
    """Remove old backup files, keeping only the specified number"""
    try:
        # Get all backup files
        db_backups = glob.glob(os.path.join(backup_path, "keepstone_backup_*.db"))
        archive_backups = glob.glob(os.path.join(backup_path, "keepstone_backup_*.tar.gz"))
        
        # Sort by modification time (newest first)
        db_backups.sort(key=os.path.getmtime, reverse=True)
        archive_backups.sort(key=os.path.getmtime, reverse=True)
        
        # Remove old database backups
        for old_backup in db_backups[keep_count:]:
            os.remove(old_backup)
            logger.info(f"Removed old database backup: {os.path.basename(old_backup)}")
        
        # Remove old archive backups
        for old_backup in archive_backups[keep_count:]:
            os.remove(old_backup)
            logger.info(f"Removed old archive backup: {os.path.basename(old_backup)}")
            
    except Exception as e:
        logger.error(f"Error cleaning up old backups: {str(e)}")

def create_weekly_backup(config):
    """Create a weekly backup of the database and optionally images"""
    try:
        backup_config = config.get('backup', {})
        backup_path = backup_config.get('backup_path', '/app/backups')
        keep_backups = backup_config.get('keep_backups', 4)
        backup_database = backup_config.get('backup_database', True)
        backup_images = backup_config.get('backup_images', False)
        
        # Create backup directory if it doesn't exist
        os.makedirs(backup_path, exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Backup database
        if backup_database:
            db_config = config.get('sql_alchemy', {})
            db_path = os.path.join(db_config.get('loc', '/app/db'), db_config.get('db', 'data.db'))
            backup_db_path = os.path.join(backup_path, f"keepstone_backup_{timestamp}.db")
            
            if os.path.exists(db_path):
                shutil.copy2(db_path, backup_db_path)
                logger.info(f"Database backup created: {backup_db_path}")
            else:
                logger.warning(f"Database file not found: {db_path}")
        
        # Backup images if enabled
        if backup_images:
            storage_config = config.get('storage', {})
            image_path = storage_config.get('image_path', 'static/uploads')
            
            # Convert relative path to absolute if needed
            if not os.path.isabs(image_path):
                image_path = os.path.join('/app', image_path)
            
            if os.path.exists(image_path):
                archive_path = os.path.join(backup_path, f"keepstone_backup_{timestamp}.tar.gz")
                
                # Create tar.gz archive of images
                import tarfile
                with tarfile.open(archive_path, 'w:gz') as tar:
                    tar.add(image_path, arcname='uploads')
                
                logger.info(f"Images backup created: {archive_path}")
            else:
                logger.warning(f"Images directory not found: {image_path}")
        
        # Clean up old backups
        cleanup_old_backups(backup_path, keep_backups)
        
        # Update last backup date
        set_last_backup_date(date.today())
        
        logger.info(f"Weekly backup completed successfully at {timestamp}")
        
    except Exception as e:
        logger.error(f"Error creating weekly backup: {str(e)}")
        raise

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
            
            # Check if weekly backup should run
            if should_run_backup(config):
                logger.info("Starting weekly backup...")
                create_weekly_backup(config)
            else:
                logger.debug("Weekly backup not scheduled for today")
                
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
    import argparse
    
    parser = argparse.ArgumentParser(description='Keepstone Scheduler')
    parser.add_argument('--backup', action='store_true', help='Force run backup now')
    parser.add_argument('--backup-images', action='store_true', help='Include images in forced backup')
    args = parser.parse_args()
    
    if args.backup:
        logger.info("Running manual backup...")
        # Override backup settings for manual run
        backup_config = config.get('backup', {}).copy()
        backup_config['enabled'] = True
        if args.backup_images:
            backup_config['backup_images'] = True
        
        # Temporarily update config
        config['backup'] = backup_config
        create_weekly_backup(config)
        logger.info("Manual backup completed")
    else:
        run_scheduler()