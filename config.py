import os
from dotenv import load_dotenv
import sys

# Load environment variables
env_path = os.path.join(os.getcwd(), '.env')
load_dotenv(env_path)

# Azure Speech Services configuration
AZURE_SPEECH_KEY = os.getenv('AZURE_SPEECH_KEY')
AZURE_SPEECH_REGION = os.getenv('AZURE_SPEECH_REGION')

# Azure OpenAI configuration
AZURE_OPENAI_API_KEY = os.getenv('AZURE_OPENAI_API_KEY')
AZURE_OPENAI_ENDPOINT = os.getenv('AZURE_OPENAI_ENDPOINT')
AZURE_OPENAI_API_VERSION = "2023-05-15"
AZURE_OPENAI_DEPLOYMENT = "gpt-35-turbo"

# Email configuration
EMAIL_USER = os.getenv('EMAIL_USER')
EMAIL_PASSWORD = os.getenv('EMAIL_PASSWORD')
EMAIL_SMTP_SERVER = os.getenv('EMAIL_SMTP_SERVER')
EMAIL_SMTP_PORT = int(os.getenv('EMAIL_SMTP_PORT', '587'))

def validate_config():
    """Validate that all required environment variables are set."""
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
        print(f"Missing required environment variables: {', '.join(missing_vars)}")
        return False
    
    return True

# Clean up OpenAI endpoint
if AZURE_OPENAI_ENDPOINT:
    AZURE_OPENAI_ENDPOINT = AZURE_OPENAI_ENDPOINT.rstrip('/')
    if AZURE_OPENAI_ENDPOINT.endswith('/openai'):
        AZURE_OPENAI_ENDPOINT = AZURE_OPENAI_ENDPOINT[:-7] 