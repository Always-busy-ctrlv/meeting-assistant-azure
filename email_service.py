import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from config import (
    EMAIL_USER,
    EMAIL_PASSWORD,
    EMAIL_SMTP_SERVER,
    EMAIL_SMTP_PORT
)

def send_meeting_summary(participants, summary):
    """Send meeting summary to participants via email."""
    if not participants:
        return False, "No recipients specified"
    
    if not summary:
        return False, "No summary content provided"
    
    try:
        # Create message
        msg = MIMEMultipart()
        msg['From'] = EMAIL_USER
        msg['To'] = ", ".join(participants)
        msg['Subject'] = f"Meeting Summary - {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        
        # Add body
        msg.attach(MIMEText(summary, 'plain'))
        
        # Connect to SMTP server
        with smtplib.SMTP(EMAIL_SMTP_SERVER, int(EMAIL_SMTP_PORT)) as server:
            server.starttls()  # Enable TLS
            server.login(EMAIL_USER, EMAIL_PASSWORD)
            server.send_message(msg)
        
        return True, "Email sent successfully"
    except smtplib.SMTPAuthenticationError as e:
        error_msg = str(e)
        if "Application-specific password required" in error_msg:
            return False, "Gmail requires an App Password. Please generate one in your Google Account settings."
        return False, f"Authentication failed: {error_msg}"
    except smtplib.SMTPException as e:
        return False, f"SMTP error: {str(e)}"
    except Exception as e:
        print(f"Error sending email: {str(e)}")
        return False, f"Failed to send email: {str(e)}" 