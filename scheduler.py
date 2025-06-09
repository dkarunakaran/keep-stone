import logging
import yaml
import sys
import os
from sqlalchemy.orm import sessionmaker
from datetime import datetime, date
from models.base import engine
from email_utils import check_expiring_tokens

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/var/log/keepstone/scheduler.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)
Session = sessionmaker(bind=engine)

def run_scheduler():
    try:
        # Load configuration
        with open('/app/config.yaml', 'r') as f:
            config = yaml.safe_load(f)
        
        # Create database session
        session = Session()
        
        try:
            # Run the check immediately
            check_expiring_tokens(session, config)
            logger.info("Scheduler check completed")
        except Exception as e:
            logger.error(f"Error running scheduled check: {str(e)}")
        finally:
            session.close()
            
    except Exception as e:
        logger.error(f"Error in scheduler setup: {str(e)}")
        if 'session' in locals():
            session.close()
        sys.exit(1)

if __name__ == "__main__":
    run_scheduler()