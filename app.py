import os
from datetime import datetime
from flask import Flask, render_template, jsonify, request, make_response
from flask_socketio import SocketIO
import azure.cognitiveservices.speech as speechsdk
import requests
from dotenv import load_dotenv
import sys
import traceback
import time
import json
import sqlite3
from pathlib import Path
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from config import validate_config
from database import init_db, get_all_meetings, update_meeting_participants, save_meeting
from transcriber import MeetingTranscriber
from email_service import send_meeting_summary
import logging
from werkzeug.exceptions import HTTPException

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Print current working directory
print(f"Current working directory: {os.getcwd()}")

# Try to load .env file
env_path = os.path.join(os.getcwd(), '.env')
print(f"Looking for .env file at: {env_path}")
print(f".env file exists: {os.path.exists(env_path)}")

# Load environment variables
load_dotenv(env_path)

# Debug: Print all environment variables
print("\nAll environment variables:")
for key in os.environ:
    if any(azure_key in key.lower() for azure_key in ['azure', 'cosmos', 'email']):
        value = os.environ[key]
        masked_value = '*' * len(value) if value else 'Not set'
        print(f"{key}: {masked_value}")

# Validate required environment variables
required_vars = [
    'AZURE_SPEECH_KEY',
    'AZURE_SPEECH_REGION',
    'AZURE_OPENAI_API_KEY',
    'AZURE_OPENAI_ENDPOINT',
    'EMAIL_USER',
    'EMAIL_PASSWORD',
    'EMAIL_SMTP_SERVER',
    'EMAIL_SMTP_PORT'
]

missing_vars = [var for var in required_vars if not os.getenv(var)]
if missing_vars:
    print("\nMissing environment variables:")
    for var in missing_vars:
        print(f"- {var}")
    print("\nPlease create a .env file with these variables.")
    sys.exit(1)

# Validate configuration
validate_config()

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key'
socketio = SocketIO(app, cors_allowed_origins="*")

# Initialize database
init_db()

# Global transcriber instance
transcriber = None

# Email configuration
EMAIL_USER = os.getenv('EMAIL_USER')
EMAIL_PASSWORD = os.getenv('EMAIL_PASSWORD')
EMAIL_SMTP_SERVER = os.getenv('EMAIL_SMTP_SERVER')
EMAIL_SMTP_PORT = int(os.getenv('EMAIL_SMTP_PORT'))

def send_email(to_emails, subject, body):
    try:
        msg = MIMEMultipart()
        msg['From'] = EMAIL_USER
        msg['To'] = ', '.join(to_emails)
        msg['Subject'] = subject

        msg.attach(MIMEText(body, 'plain'))

        server = smtplib.SMTP(EMAIL_SMTP_SERVER, EMAIL_SMTP_PORT)
        server.starttls()
        server.login(EMAIL_USER, EMAIL_PASSWORD)
        server.send_message(msg)
        server.quit()
        return True, "Email sent successfully"
    except Exception as e:
        print(f"Error sending email: {str(e)}")
        return False, str(e)

# Azure Speech Services configuration
print("\nInitializing Speech Services...")
speech_key = os.getenv('AZURE_SPEECH_KEY')
speech_region = os.getenv('AZURE_SPEECH_REGION')
print(f"Speech Region: {speech_region}")

speech_config = speechsdk.SpeechConfig(
    subscription=speech_key,
    region=speech_region
)

# Configure speech recognition settings
speech_config.speech_recognition_language = "en-US"
speech_config.set_property(speechsdk.PropertyId.SpeechServiceConnection_InitialSilenceTimeoutMs, "5000")
speech_config.set_property(speechsdk.PropertyId.SpeechServiceConnection_EndSilenceTimeoutMs, "1000")

# Azure OpenAI configuration
API_KEY = os.getenv('AZURE_OPENAI_API_KEY')
API_ENDPOINT = os.getenv('AZURE_OPENAI_ENDPOINT')
API_VERSION = "2023-05-15"  # Using stable version
DEPLOYMENT_NAME = "gpt-35-turbo"

# Clean up the API endpoint
API_ENDPOINT = API_ENDPOINT.rstrip('/')
if API_ENDPOINT.endswith('/openai'):
    API_ENDPOINT = API_ENDPOINT[:-7]  # Remove /openai if it exists

print("\nOpenAI Configuration:")
print(f"API Endpoint: {API_ENDPOINT}")
print(f"API Version: {API_VERSION}")
print(f"Deployment Name: {DEPLOYMENT_NAME}")

@app.route('/')
def index():
    return make_response(render_template('index.html'))

@app.route('/meetings')
def list_meetings():
    meetings = get_all_meetings()
    return make_response(jsonify(meetings))

@app.route('/start_meeting', methods=['POST'])
def start_meeting():
    global transcriber
    try:
        logger.info("Starting new meeting...")
        transcriber = MeetingTranscriber(socketio)
        transcriber.start_recording()
        logger.info("Meeting started successfully")
        return make_response(jsonify({'status': 'success', 'message': 'Meeting started'}))
    except Exception as e:
        logger.error(f"Error starting meeting: {str(e)}")
        return make_response(jsonify({'status': 'error', 'message': str(e)}), 500)

@app.route('/end_meeting', methods=['POST'])
def end_meeting():
    global transcriber
    try:
        logger.info("Ending meeting...")
        if transcriber:
            transcript = transcriber.stop_recording()
            summary = transcriber.generate_summary(transcript)
            save_meeting(transcript, summary)
            logger.info("Meeting ended successfully")
            return make_response(jsonify({
                'status': 'success',
                'message': 'Meeting ended',
                'summary': summary
            }))
        else:
            logger.error("No active meeting to end")
            return make_response(jsonify({'status': 'error', 'message': 'No active meeting'}), 400)
    except Exception as e:
        logger.error(f"Error ending meeting: {str(e)}")
        return make_response(jsonify({'status': 'error', 'message': str(e)}), 500)

@app.route('/send_email', methods=['POST'])
def send_email():
    try:
        data = request.get_json()
        if not data or 'participants' not in data or 'summary' not in data:
            return make_response(jsonify({'status': 'error', 'message': 'Missing required data'}), 400)
        
        participants = data['participants']
        summary = data['summary']
        
        if not participants or not summary:
            return make_response(jsonify({'status': 'error', 'message': 'Participants and summary are required'}), 400)
        
        result = send_meeting_summary(participants, summary)
        return make_response(jsonify(result))
    except Exception as e:
        logger.error(f"Error sending email: {str(e)}")
        return make_response(jsonify({'status': 'error', 'message': str(e)}), 500)

@socketio.on('connect')
def handle_connect():
    logger.info('Client connected')

@socketio.on('disconnect')
def handle_disconnect():
    logger.info('Client disconnected')

@app.errorhandler(Exception)
def handle_error(e):
    logger.error(f"Unhandled error: {str(e)}")
    if isinstance(e, HTTPException):
        return jsonify({
            'status': 'error',
            'message': e.description
        }), e.code
    return jsonify({
        'status': 'error',
        'message': 'Internal server error'
    }), 500

if __name__ == '__main__':
    try:
        init_db()
        # Get port from environment variable (Azure App Service sets this)
        port = int(os.getenv('PORT', 5000))
        
        # Always use Gunicorn in production
        from gunicorn.app.base import BaseApplication

        class SocketIOApplication(BaseApplication):
            def __init__(self, app, options=None):
                self.options = options or {}
                self.application = app
                super().__init__()

            def load_config(self):
                for key, value in self.options.items():
                    self.cfg.set(key, value)

            def load(self):
                return self.application

        options = {
            'bind': f'0.0.0.0:{port}',
            'workers': 1,
            'threads': 8,
            'timeout': 120,
            'accesslog': '-',
            'errorlog': '-',
            'loglevel': 'info'
        }
        SocketIOApplication(app, options).run()
    except Exception as e:
        logger.error(f"Failed to start server: {str(e)}")
        raise 