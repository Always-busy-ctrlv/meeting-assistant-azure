import os
from datetime import datetime
from flask import Flask, render_template, jsonify, request, make_response, send_from_directory
from flask_socketio import SocketIO, emit
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
from config import validate_config, AZURE_SPEECH_KEY, AZURE_SPEECH_REGION, AZURE_OPENAI_API_KEY, AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_API_VERSION, AZURE_OPENAI_DEPLOYMENT
from database import init_db, get_all_meetings, update_meeting_participants, save_meeting
from transcriber import MeetingTranscriber
from email_service import send_meeting_summary
import logging
from werkzeug.exceptions import HTTPException
import openai
from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient
from azure.openai import AzureOpenAI
from azure.storage.blob import BlobServiceClient
from azure.cosmos import CosmosClient
from azure.search.documents import SearchClient
from azure.ai.formrecognizer import DocumentAnalysisClient
from azure.ai.textanalytics import TextAnalyticsClient
from azure.ai.translation.document import DocumentTranslationClient
from azure.ai.language.conversations import ConversationAnalysisClient
from azure.ai.personalizer import PersonalizerClient
from azure.ai.metricsadvisor import MetricsAdvisorClient
from azure.ai.anomalydetector import AnomalyDetectorClient
from azure.ai.contentsafety import ContentSafetyClient
from azure.ai.generative import GenerativeClient
from azure.ai.ml import MLClient
from azure.ai.documentintelligence import DocumentIntelligenceClient

# Configure logging
logging.basicConfig(level=logging.INFO)
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
app = Flask(__name__, static_folder='static', static_url_path='/static')
app.config['SECRET_KEY'] = os.urandom(24)

# Initialize SocketIO with default settings
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

# Initialize Azure Key Vault client
key_vault_url = os.getenv('AZURE_KEY_VAULT_URL')
credential = DefaultAzureCredential()
secret_client = SecretClient(vault_url=key_vault_url, credential=credential)

# Get secrets from Key Vault
openai_api_key = secret_client.get_secret('openai-api-key').value
openai_api_base = secret_client.get_secret('openai-api-base').value
openai_api_version = secret_client.get_secret('openai-api-version').value
openai_api_type = secret_client.get_secret('openai-api-type').value

# Configure OpenAI client
openai.api_key = openai_api_key
openai.api_base = openai_api_base
openai.api_version = openai_api_version
openai.api_type = openai_api_type

# Initialize transcriber
transcriber = MeetingTranscriber(socketio)

# Azure OpenAI Configuration
try:
    client = AzureOpenAI(
        api_key=os.environ.get("AZURE_OPENAI_API_KEY"),
        api_version=os.environ.get("AZURE_OPENAI_API_VERSION", "2024-02-15-preview"),
        azure_endpoint=os.environ.get("AZURE_OPENAI_ENDPOINT")
    )
    logger.info("Azure OpenAI client initialized successfully")
except Exception as e:
    logger.error(f"Error initializing Azure OpenAI client: {str(e)}")
    client = None

# Azure Speech Configuration
try:
    speech_config = speechsdk.SpeechConfig(
        subscription=os.environ.get("AZURE_SPEECH_KEY"),
        region=os.environ.get("AZURE_SPEECH_REGION")
    )
    logger.info("Azure Speech client initialized successfully")
except Exception as e:
    logger.error(f"Error initializing Azure Speech client: {str(e)}")
    speech_config = None

# Initialize other Azure clients
try:
    # Azure Key Vault
    credential = DefaultAzureCredential()
    key_vault_url = os.environ.get("AZURE_KEY_VAULT_URL")
    if key_vault_url:
        secret_client = SecretClient(vault_url=key_vault_url, credential=credential)
        logger.info("Azure Key Vault client initialized successfully")
    else:
        secret_client = None
        logger.warning("Azure Key Vault URL not provided")

    # Azure Blob Storage
    blob_connection_string = os.environ.get("AZURE_STORAGE_CONNECTION_STRING")
    if blob_connection_string:
        blob_service_client = BlobServiceClient.from_connection_string(blob_connection_string)
        logger.info("Azure Blob Storage client initialized successfully")
    else:
        blob_service_client = None
        logger.warning("Azure Storage connection string not provided")

    # Azure Cosmos DB
    cosmos_endpoint = os.environ.get("AZURE_COSMOS_ENDPOINT")
    cosmos_key = os.environ.get("AZURE_COSMOS_KEY")
    if cosmos_endpoint and cosmos_key:
        cosmos_client = CosmosClient(cosmos_endpoint, cosmos_key)
        logger.info("Azure Cosmos DB client initialized successfully")
    else:
        cosmos_client = None
        logger.warning("Azure Cosmos DB credentials not provided")

    # Azure Cognitive Search
    search_endpoint = os.environ.get("AZURE_SEARCH_ENDPOINT")
    search_key = os.environ.get("AZURE_SEARCH_KEY")
    if search_endpoint and search_key:
        search_client = SearchClient(endpoint=search_endpoint, credential=search_key)
        logger.info("Azure Cognitive Search client initialized successfully")
    else:
        search_client = None
        logger.warning("Azure Cognitive Search credentials not provided")

    # Azure Form Recognizer
    form_endpoint = os.environ.get("AZURE_FORM_RECOGNIZER_ENDPOINT")
    form_key = os.environ.get("AZURE_FORM_RECOGNIZER_KEY")
    if form_endpoint and form_key:
        form_client = DocumentAnalysisClient(endpoint=form_endpoint, credential=form_key)
        logger.info("Azure Form Recognizer client initialized successfully")
    else:
        form_client = None
        logger.warning("Azure Form Recognizer credentials not provided")

    # Azure Text Analytics
    text_endpoint = os.environ.get("AZURE_TEXT_ANALYTICS_ENDPOINT")
    text_key = os.environ.get("AZURE_TEXT_ANALYTICS_KEY")
    if text_endpoint and text_key:
        text_client = TextAnalyticsClient(endpoint=text_endpoint, credential=text_key)
        logger.info("Azure Text Analytics client initialized successfully")
    else:
        text_client = None
        logger.warning("Azure Text Analytics credentials not provided")

    # Azure Document Translation
    translation_endpoint = os.environ.get("AZURE_TRANSLATION_ENDPOINT")
    translation_key = os.environ.get("AZURE_TRANSLATION_KEY")
    if translation_endpoint and translation_key:
        translation_client = DocumentTranslationClient(endpoint=translation_endpoint, credential=translation_key)
        logger.info("Azure Document Translation client initialized successfully")
    else:
        translation_client = None
        logger.warning("Azure Document Translation credentials not provided")

    # Azure Language Understanding
    language_endpoint = os.environ.get("AZURE_LANGUAGE_ENDPOINT")
    language_key = os.environ.get("AZURE_LANGUAGE_KEY")
    if language_endpoint and language_key:
        language_client = ConversationAnalysisClient(endpoint=language_endpoint, credential=language_key)
        logger.info("Azure Language Understanding client initialized successfully")
    else:
        language_client = None
        logger.warning("Azure Language Understanding credentials not provided")

    # Azure Personalizer
    personalizer_endpoint = os.environ.get("AZURE_PERSONALIZER_ENDPOINT")
    personalizer_key = os.environ.get("AZURE_PERSONALIZER_KEY")
    if personalizer_endpoint and personalizer_key:
        personalizer_client = PersonalizerClient(endpoint=personalizer_endpoint, credential=personalizer_key)
        logger.info("Azure Personalizer client initialized successfully")
    else:
        personalizer_client = None
        logger.warning("Azure Personalizer credentials not provided")

    # Azure Metrics Advisor
    metrics_endpoint = os.environ.get("AZURE_METRICS_ADVISOR_ENDPOINT")
    metrics_key = os.environ.get("AZURE_METRICS_ADVISOR_KEY")
    if metrics_endpoint and metrics_key:
        metrics_client = MetricsAdvisorClient(endpoint=metrics_endpoint, credential=metrics_key)
        logger.info("Azure Metrics Advisor client initialized successfully")
    else:
        metrics_client = None
        logger.warning("Azure Metrics Advisor credentials not provided")

    # Azure Anomaly Detector
    anomaly_endpoint = os.environ.get("AZURE_ANOMALY_DETECTOR_ENDPOINT")
    anomaly_key = os.environ.get("AZURE_ANOMALY_DETECTOR_KEY")
    if anomaly_endpoint and anomaly_key:
        anomaly_client = AnomalyDetectorClient(endpoint=anomaly_endpoint, credential=anomaly_key)
        logger.info("Azure Anomaly Detector client initialized successfully")
    else:
        anomaly_client = None
        logger.warning("Azure Anomaly Detector credentials not provided")

    # Azure Content Safety
    safety_endpoint = os.environ.get("AZURE_CONTENT_SAFETY_ENDPOINT")
    safety_key = os.environ.get("AZURE_CONTENT_SAFETY_KEY")
    if safety_endpoint and safety_key:
        safety_client = ContentSafetyClient(endpoint=safety_endpoint, credential=safety_key)
        logger.info("Azure Content Safety client initialized successfully")
    else:
        safety_client = None
        logger.warning("Azure Content Safety credentials not provided")

    # Azure AI Generative
    generative_endpoint = os.environ.get("AZURE_AI_GENERATIVE_ENDPOINT")
    generative_key = os.environ.get("AZURE_AI_GENERATIVE_KEY")
    if generative_endpoint and generative_key:
        generative_client = GenerativeClient(endpoint=generative_endpoint, credential=generative_key)
        logger.info("Azure AI Generative client initialized successfully")
    else:
        generative_client = None
        logger.warning("Azure AI Generative credentials not provided")

    # Azure Machine Learning
    ml_endpoint = os.environ.get("AZURE_ML_ENDPOINT")
    ml_key = os.environ.get("AZURE_ML_KEY")
    if ml_endpoint and ml_key:
        ml_client = MLClient(endpoint=ml_endpoint, credential=ml_key)
        logger.info("Azure Machine Learning client initialized successfully")
    else:
        ml_client = None
        logger.warning("Azure Machine Learning credentials not provided")

    # Azure Document Intelligence
    doc_intel_endpoint = os.environ.get("AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT")
    doc_intel_key = os.environ.get("AZURE_DOCUMENT_INTELLIGENCE_KEY")
    if doc_intel_endpoint and doc_intel_key:
        doc_intel_client = DocumentIntelligenceClient(endpoint=doc_intel_endpoint, credential=doc_intel_key)
        logger.info("Azure Document Intelligence client initialized successfully")
    else:
        doc_intel_client = None
        logger.warning("Azure Document Intelligence credentials not provided")

except Exception as e:
    logger.error(f"Error initializing Azure clients: {str(e)}")

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
    return render_template('index.html')

@app.route('/meetings')
def list_meetings():
    meetings = get_all_meetings()
    return make_response(jsonify(meetings))

@socketio.on('start_meeting')
def handle_start_meeting():
    try:
        transcriber.start_transcription()
        emit('meeting_started', {'status': 'success'})
    except Exception as e:
        logger.error(f"Error starting meeting: {str(e)}")
        emit('error', {'message': str(e)})

@socketio.on('stop_meeting')
def handle_stop_meeting():
    try:
        transcriber.stop_transcription()
        emit('meeting_stopped', {'status': 'success'})
    except Exception as e:
        logger.error(f"Error stopping meeting: {str(e)}")
        emit('error', {'message': str(e)})

@socketio.on('transcription')
def handle_transcription(data):
    try:
        text = data.get('text', '')
        if text:
            transcriber.process_transcription(text)
    except Exception as e:
        logger.error(f"Error processing transcription: {str(e)}")
        emit('error', {'message': str(e)})

@app.route('/api/summary', methods=['GET'])
def get_summary():
    try:
        summary = transcriber.get_summary()
        return jsonify({"status": "success", "summary": summary})
    except Exception as e:
        logger.error(f"Error getting summary: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

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

@app.route('/static/<path:filename>')
def serve_static(filename):
    try:
        return send_from_directory(app.static_folder, filename)
    except Exception as e:
        logger.error(f"Error serving static file {filename}: {str(e)}")
        return make_response(jsonify({'status': 'error', 'message': 'File not found'}), 404)

@socketio.on('connect')
def handle_connect():
    logger.info("Client connected")

@socketio.on('disconnect')
def handle_disconnect():
    logger.info("Client disconnected")

@socketio.on('audio_data')
def handle_audio_data(data):
    try:
        # Process audio data
        logger.info('Received audio data')
        # Add your audio processing logic here
        socketio.emit('processing_status', {'status': 'processing'})
    except Exception as e:
        logger.error(f"Error processing audio data: {str(e)}")
        socketio.emit('error', {'message': str(e)})

@app.errorhandler(Exception)
def handle_error(e):
    if isinstance(e, HTTPException):
        response = e.get_response()
        response.data = json.dumps({
            "code": e.code,
            "name": e.name,
            "description": e.description,
        })
        response.content_type = "application/json"
        return response
    
    logger.error(f"Unhandled error: {str(e)}")
    return make_response(jsonify({
        'status': 'error',
        'message': str(e)
    }), 500)

if __name__ == '__main__':
    # Create static directory if it doesn't exist
    static_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static')
    if not os.path.exists(static_dir):
        os.makedirs(static_dir)
    
    # Create static/css and static/js directories
    for subdir in ['css', 'js']:
        subdir_path = os.path.join(static_dir, subdir)
        if not os.path.exists(subdir_path):
            os.makedirs(subdir_path)
    
    # Start the application
    port = int(os.environ.get('PORT', 8000))
    socketio.run(app, host='0.0.0.0', port=port, debug=False) 