import azure.cognitiveservices.speech as speechsdk
import requests
import traceback
import time
from config import (
    AZURE_SPEECH_KEY,
    AZURE_SPEECH_REGION,
    AZURE_OPENAI_API_KEY,
    AZURE_OPENAI_ENDPOINT,
    AZURE_OPENAI_API_VERSION,
    AZURE_OPENAI_DEPLOYMENT
)
from database import save_meeting
from flask_socketio import SocketIO
from openai import AzureOpenAI
import logging
import json

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Configure OpenAI client
client = AzureOpenAI(
    api_key=AZURE_OPENAI_API_KEY,
    api_version=AZURE_OPENAI_API_VERSION,
    azure_endpoint=AZURE_OPENAI_ENDPOINT
)

class MeetingTranscriber:
    def __init__(self, socketio=None):
        """Initialize the transcriber with Azure Speech Services configuration."""
        self.speech_config = speechsdk.SpeechConfig(
            subscription=AZURE_SPEECH_KEY,
            region=AZURE_SPEECH_REGION
        )
        self.speech_config.speech_recognition_language = "en-US"
        
        # Configure speech recognition settings
        self.speech_config.set_property(
            speechsdk.PropertyId.SpeechServiceConnection_InitialSilenceTimeoutMs,
            "5000"
        )
        self.speech_config.set_property(
            speechsdk.PropertyId.SpeechServiceConnection_EndSilenceTimeoutMs,
            "5000"
        )
        
        # Enable word-level timestamps for better speaker tracking
        self.speech_config.set_property(
            speechsdk.PropertyId.SpeechServiceResponse_RequestWordLevelTimestamps,
            "true"
        )
        
        # Enable detailed results
        self.speech_config.set_property(
            speechsdk.PropertyId.SpeechServiceResponse_RequestDetailedResultTrueFalse,
            "true"
        )
        
        self.audio_config = speechsdk.audio.AudioConfig(use_default_microphone=True)
        self.transcript = []
        self.speaker_transcript = []  # Store speaker-specific transcript
        self.socketio = socketio
        self.recognizer = None
        self.current_speaker = None
        self.speaker_count = 0
        self.last_speaker_time = time.time()

    def handle_result(self, evt):
        """Handle speech recognition results with speaker identification"""
        try:
            result = evt.result
            text = result.text
            
            # Simple speaker tracking based on silence duration
            current_time = time.time()
            if current_time - self.last_speaker_time > 2.0:  # If more than 2 seconds of silence
                self.speaker_count = (self.speaker_count + 1) % 4  # Cycle through 4 speakers
                self.current_speaker = f"Speaker {self.speaker_count + 1}"
            
            self.last_speaker_time = current_time
            
            # Create transcript entry with speaker information
            transcript_entry = {
                'text': text,
                'speaker': self.current_speaker or "Speaker 1",
                'timestamp': time.strftime('%H:%M:%S'),
                'speaker_id': self.speaker_count + 1
            }
            
            self.transcript.append(text)
            self.speaker_transcript.append(transcript_entry)
            
            # Emit the transcript update through Socket.IO with speaker information
            if self.socketio:
                self.socketio.emit('transcript_update', transcript_entry)
                print(f"Emitted transcript update: {json.dumps(transcript_entry)}")
                
        except Exception as e:
            print(f"Error in handle_result: {str(e)}")
            import traceback
            traceback.print_exc()

    def handle_canceled(self, evt):
        """Handle speech recognition cancellation"""
        try:
            print(f"Speech recognition canceled: {evt.result.text}")
            print(f"Reason: {evt.result.reason}")
            if evt.result.reason == speechsdk.CancellationReason.Error:
                print(f"Error details: {evt.result.error_details}")
        except Exception as e:
            print(f"Error in handle_canceled: {str(e)}")
            import traceback
            traceback.print_exc()

    def handle_session_started(self, evt):
        """Handle speech recognition session start"""
        try:
            print(f"Speech recognition session started: {evt.session_id}")
        except Exception as e:
            print(f"Error in handle_session_started: {str(e)}")
            import traceback
            traceback.print_exc()

    def handle_session_stopped(self, evt):
        """Handle speech recognition session stop"""
        try:
            print(f"Speech recognition session stopped: {evt.session_id}")
        except Exception as e:
            print(f"Error in handle_session_stopped: {str(e)}")
            import traceback
            traceback.print_exc()

    def start_recording(self):
        """Start the speech recognition session"""
        try:
            print("Starting recording...")
            print("Configuring audio input...")
            
            # Create speech recognizer
            self.recognizer = speechsdk.SpeechRecognizer(
                speech_config=self.speech_config,
                audio_config=self.audio_config
            )
            
            # Connect event handlers
            print("Connecting event handlers...")
            self.recognizer.recognized.connect(self.handle_result)
            self.recognizer.canceled.connect(self.handle_canceled)
            self.recognizer.session_started.connect(self.handle_session_started)
            self.recognizer.session_stopped.connect(self.handle_session_stopped)
            
            print("Starting continuous recognition...")
            self.recognizer.start_continuous_recognition()
            print("Recording started successfully")
        except Exception as e:
            print(f"Error starting recording: {str(e)}")
            import traceback
            traceback.print_exc()
            raise

    def stop_recording(self):
        """Stop recording and return the transcript with speaker information."""
        try:
            if self.recognizer:
                print("Stopping continuous recognition...")
                self.recognizer.stop_continuous_recognition()
                
                # Format the transcript with speaker information
                formatted_transcript = []
                for entry in self.speaker_transcript:
                    formatted_transcript.append(
                        f"[{entry['timestamp']}] {entry['speaker']}: {entry['text']}"
                    )
                
                full_transcript = "\n".join(formatted_transcript)
                print(f"Full transcript with speakers: {full_transcript}")
                return full_transcript
            return ""
        except Exception as e:
            print(f"Error stopping recording: {str(e)}")
            import traceback
            traceback.print_exc()
            return ""

    def generate_summary(self, transcript=None):
        """Generate a summary of the transcript using Azure OpenAI with speaker-specific action items."""
        try:
            if not transcript:
                # Format the transcript with speaker information for better context
                formatted_transcript = []
                for entry in self.speaker_transcript:
                    formatted_transcript.append(
                        f"[{entry['timestamp']}] {entry['speaker']}: {entry['text']}"
                    )
                transcript = "\n".join(formatted_transcript)
            
            if not transcript:
                return "No transcript available to summarize."
            
            print("Generating summary using Azure OpenAI...")
            print(f"Using deployment: {AZURE_OPENAI_DEPLOYMENT}")
            print(f"Using endpoint: {AZURE_OPENAI_ENDPOINT}")
            print(f"Transcript length: {len(transcript)} characters")
            
            response = client.chat.completions.create(
                model=AZURE_OPENAI_DEPLOYMENT,
                messages=[
                    {"role": "system", "content": """You are a helpful assistant that summarizes meeting transcripts. 
                    Your response should be structured in three parts:
                    1. A concise summary of the main points discussed
                    2. A list of action items, organized by speaker
                    3. A general list of action items that aren't speaker-specific
                    
                    For speaker-specific action items, use the format:
                    [Speaker Name]'s Action Items:
                    - Item 1
                    - Item 2
                    
                    For general action items, use the format:
                    General Action Items:
                    - Item 1
                    - Item 2"""},
                    {"role": "user", "content": f"""Please provide a summary and action items for this meeting transcript:

{transcript}

Please structure your response as follows:
1. First, provide a concise summary of the main points discussed
2. Then, list all action items organized by speaker (if any speaker-specific items are identified)
3. Finally, list any general action items that aren't specific to a particular speaker
4. Format all action items as bulleted lists"""}
                ],
                temperature=0.7,
                max_tokens=1000
            )
            
            summary = response.choices[0].message.content
            print(f"Generated summary: {summary[:200]}...")
            return summary
        except Exception as e:
            print(f"Error generating summary: {str(e)}")
            import traceback
            traceback.print_exc()
            return f"Error generating summary: {str(e)}" 