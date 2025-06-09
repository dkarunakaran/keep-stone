from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
import pytz
from email_utils import check_expiring_tokens
import yaml
import logging
from sqlalchemy.orm import sessionmaker
import sys
import os
import sys
parent_dir = ".."
sys.path.append(parent_dir)
import models.base


Session = sessionmaker(bind=models.base.engine)

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def run_scheduler():
    try:
        # Load configuration
        with open('config.yaml', 'r') as f:
            config = yaml.safe_load(f)
        
        # Create database session
        session = Session()
        
        # Initialize scheduler
        scheduler = BackgroundScheduler()
        timezone = pytz.timezone(config['email']['timezone'])
        
        # Add email checking job
        scheduler.add_job(
            func=check_expiring_tokens,
            trigger=CronTrigger(
                hour=config['email']['trigger_hour'],
                minute=config['email']['trigger_minute'],
                timezone=timezone
            ),
            args=[session, config],
            id='check_expiring_tokens',
            name='Check expiring tokens and send notifications',
            replace_existing=True,
            misfire_grace_time=3600
        )
        
        scheduler.start()
        logger.info("Scheduler started successfully")
        
        # Keep the script running
        try:
            while True:
                pass
        except KeyboardInterrupt:
            scheduler.shutdown()
            session.close()
            
    except Exception as e:
        logger.error(f"Error in scheduler: {str(e)}")
        if 'scheduler' in locals():
            scheduler.shutdown()
        if 'session' in locals():
            session.close()
        sys.exit(1)

if __name__ == "__main__":
    run_scheduler()