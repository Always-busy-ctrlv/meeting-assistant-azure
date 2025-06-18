import unittest
from unittest.mock import patch, MagicMock
from transcriber import MeetingTranscriber
import azure.cognitiveservices.speech as speechsdk

class TestTranscriber(unittest.TestCase):
    def setUp(self):
        # Create mock socketio
        self.mock_socketio = MagicMock()
        self.transcriber = MeetingTranscriber(self.mock_socketio)

    @patch('azure.cognitiveservices.speech.SpeechRecognizer')
    def test_start_recording(self, mock_speech_recognizer):
        # Configure mock
        mock_recognizer = MagicMock()
        mock_speech_recognizer.return_value = mock_recognizer
        
        # Start recording
        self.transcriber.start_recording()
        
        # Verify results
        self.assertTrue(self.transcriber.is_recording)
        self.assertEqual(self.transcriber.transcript, [])
        mock_recognizer.start_continuous_recognition.assert_called_once()

    @patch('azure.cognitiveservices.speech.SpeechRecognizer')
    def test_stop_recording(self, mock_speech_recognizer):
        # Configure mock
        mock_recognizer = MagicMock()
        mock_speech_recognizer.return_value = mock_recognizer
        
        # Start recording first
        self.transcriber.start_recording()
        
        # Stop recording
        self.transcriber.stop_recording()
        
        # Verify results
        self.assertFalse(self.transcriber.is_recording)
        mock_recognizer.stop_continuous_recognition.assert_called_once()

    @patch('requests.post')
    def test_generate_summary_success(self, mock_post):
        # Configure mock response
        mock_response = MagicMock()
        mock_response.json.return_value = {
            'choices': [{'message': {'content': 'Test summary'}}]
        }
        mock_post.return_value = mock_response
        
        # Set test transcript
        self.transcriber.transcript = ["Test transcript"]
        
        # Generate summary
        summary = self.transcriber.generate_summary()
        
        # Verify results
        self.assertEqual(summary, 'Test summary')
        mock_post.assert_called_once()

    @patch('requests.post')
    def test_generate_summary_error(self, mock_post):
        # Configure mock to raise exception
        mock_post.side_effect = Exception("API Error")
        
        # Set test transcript
        self.transcriber.transcript = ["Test transcript"]
        
        # Generate summary
        summary = self.transcriber.generate_summary()
        
        # Verify results
        self.assertIn("Error generating summary", summary)
        self.assertIn("API Error", summary)

    def test_generate_summary_empty_transcript(self):
        # Test with empty transcript
        summary = self.transcriber.generate_summary()
        
        # Verify results
        self.assertEqual(summary, "No transcript available to generate summary.")

    def test_handle_result(self):
        # Create a mock event
        mock_event = MagicMock()
        mock_event.result.text = "Test recognition"
        
        # Call handle_result
        self.transcriber.handle_result(mock_event)
        
        # Verify results
        self.assertEqual(self.transcriber.transcript, ["Test recognition"])
        self.mock_socketio.emit.assert_called_once_with(
            'transcript_update',
            {'text': "Test recognition"}
        )

if __name__ == '__main__':
    unittest.main() 