# Meeting Assistant

A real-time meeting transcription and analysis application that:
- Listens to meetings as a third party
- Provides real-time transcription
- Generates meeting summaries and action items
- Stores conversation data in Azure Cosmos DB

## Prerequisites

- Python 3.8 or higher
- Azure account with the following services:
  - Azure Speech Services
  - Azure OpenAI
  - Azure Cosmos DB

## Setup

1. Clone this repository
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Create a `.env` file with your Azure credentials:
   ```
   AZURE_SPEECH_KEY=your_speech_key
   AZURE_SPEECH_REGION=your_speech_region
   AZURE_OPENAI_API_KEY=your_openai_key
   AZURE_OPENAI_ENDPOINT=your_openai_endpoint
   COSMOS_ENDPOINT=your_cosmos_endpoint
   COSMOS_KEY=your_cosmos_key
   ```

## Running the Application

1. Start the application:
   ```bash
   python app.py
   ```
2. Open your browser and navigate to `http://localhost:5000`
3. Click "Start Meeting" to begin transcription
4. Click "End Meeting" when finished to generate summary and action items

## Features

- Real-time speech-to-text transcription
- Live meeting transcript display
- Automatic summary generation
- Action item extraction
- Persistent storage of meeting data 