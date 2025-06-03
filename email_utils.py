import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import date, timedelta
import os
from dotenv import load_dotenv
from models.artifact import Artifact
from models.type import Type


load_dotenv()

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
        # Create secure SSL/TLS connection
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(sender_email, sender_password)
        server.send_message(message)
        server.quit()
        return True
    except Exception as e:
        print(f"Failed to send email notification: {str(e)}")
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
                print(f"Notification sent for {token.name} ({token.notification_count} sent)")