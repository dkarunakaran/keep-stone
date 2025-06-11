import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import date, timedelta
import os
from dotenv import load_dotenv
from models.artifact import Artifact
from models.type import Type
import logging
import sys


load_dotenv()

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

def send_expiry_notification(config, artifact, days_left):
    """Send email notification for expiring tokens"""
    sender_email = os.getenv('SENDER_EMAIL')
    sender_password = os.getenv('EMAIL_APP_PASSWORD') 
    smtp_server = config['email']['smtp_server']
    smtp_port = config['email']['smtp_port']

    # Create message
    message = MIMEMultipart()
    message["From"] = sender_email
    message["To"] = config.get('maintainer_email', sender_email)
    message["Subject"] = f"Token Expiry Alert: {artifact.name}"

    # Email body
    body = f"""
    <html>
        <body>
            <h2>Token Expiry Alert</h2>
            <p>The following token is about to expire:</p>
            <ul>
                <li><strong>Name:</strong> {artifact.name}</li>
                <li><strong>Expiry Date:</strong> {artifact.expiry_date.strftime('%B %d, %Y')}</li>
                <li><strong>Days Remaining:</strong> {days_left}</li>
            </ul>
            <p>Please take necessary action to renew or update the token.</p>
        </body>
    </html>
    """

    message.attach(MIMEText(body, "html"))

    try:
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(sender_email, sender_password)
        server.send_message(message)
        server.quit()
        logger.info(f"Sent notification for {artifact.name} ({days_left} days remaining)")
        return True
    except Exception as e:
        logger.error(f"Failed to send email notification for {artifact.name}: {str(e)}")
        return False

def check_expiring_tokens(session, config):
    """Check for tokens that will expire soon and send notifications"""
    today = date.today()
    notification_days = config['email'].get('notification_days', 14)
    
    # Get token type ID
    token_type = session.query(Type).filter(Type.name == 'Token').first()
    if not token_type:
        return
    
    # Query for tokens that will expire soon
    expiring_tokens = (
        session.query(Artifact)
        .filter(
            Artifact.type_id == token_type.id,
            Artifact.expiry_date <= today + timedelta(days=notification_days),
            Artifact.expiry_date > today
        )
        .all()
    )
    
    for token in expiring_tokens:
        if token.can_send_notification(config):
            days_left = (token.expiry_date - today).days
            if send_expiry_notification(config, token, days_left):
                token.record_notification()
                session.commit()
                logger.info(f"Notification recorded for {token.name} (total: {token.notification_count})")