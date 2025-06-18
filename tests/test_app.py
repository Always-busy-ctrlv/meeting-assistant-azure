import os
import unittest
import tempfile
import shutil
from flask import Flask
from app import app, socketio
from database import init_db, save_meeting
from unittest.mock import patch, MagicMock

class TestApp(unittest.TestCase):
    def setUp(self):
        # Create a temporary directory for the test database
        self.test_dir = tempfile.mkdtemp()
        self.test_db_path = os.path.join(self.test_dir, 'test_meetings.db')
        
        # Initialize test database
        init_db(self.test_db_path)
        
        # Configure app for testing
        app.config['TESTING'] = True
        app.config['DATABASE_PATH'] = self.test_db_path
        self.app = app.test_client()
        
        # Mock socketio
        self.socketio_patcher = patch('app.socketio')
        self.mock_socketio = self.socketio_patcher.start()

    def tearDown(self):
        # Clean up
        self.socketio_patcher.stop()
        shutil.rmtree(self.test_dir)

    def test_index_route(self):
        """Test the index route."""
        response = self.app.get('/')
        self.assertEqual(response.status_code, 200)

    def test_list_meetings_route(self):
        """Test the list meetings route."""
        # Add some test data
        save_meeting("Test transcript 1", "Test summary 1", self.test_db_path)
        save_meeting("Test transcript 2", "Test summary 2", self.test_db_path)
        
        response = self.app.get('/meetings')
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(len(data), 2)

    @patch('app.MeetingTranscriber')
    def test_start_meeting_success(self, mock_transcriber):
        """Test successful meeting start."""
        # Configure mock
        mock_instance = MagicMock()
        mock_transcriber.return_value = mock_instance
        
        response = self.app.post('/start_meeting')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json['status'], 'success')
        mock_instance.start_recording.assert_called_once()

    @patch('app.MeetingTranscriber')
    def test_start_meeting_error(self, mock_transcriber):
        """Test meeting start with error."""
        # Configure mock to raise exception
        mock_transcriber.side_effect = Exception("Test error")
        
        response = self.app.post('/start_meeting')
        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.json['status'], 'error')

    @patch('app.MeetingTranscriber')
    def test_end_meeting_success(self, mock_transcriber):
        """Test successful meeting end."""
        # Configure mock
        mock_instance = MagicMock()
        mock_instance.stop_recording.return_value = "Test transcript"
        mock_instance.generate_summary.return_value = "Test summary"
        mock_transcriber.return_value = mock_instance
        
        response = self.app.post('/end_meeting')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json['status'], 'success')
        self.assertEqual(response.json['summary'], 'Test summary')

    @patch('app.MeetingTranscriber')
    def test_end_meeting_error(self, mock_transcriber):
        """Test meeting end with error."""
        # Configure mock to raise exception
        mock_transcriber.side_effect = Exception("Test error")
        
        response = self.app.post('/end_meeting')
        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.json['status'], 'error')

    @patch('app.send_meeting_summary')
    def test_send_email_success(self, mock_send_email):
        """Test successful email sending."""
        # Configure mock
        mock_send_email.return_value = (True, "Email sent successfully")
        
        # Test data
        test_data = {
            'summary': 'Test summary',
            'participants': ['test@example.com']
        }
        
        response = self.app.post('/send_email', json=test_data)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json['status'], 'success')
        mock_send_email.assert_called_once_with(['test@example.com'], 'Test summary')

    @patch('app.send_meeting_summary')
    def test_send_email_error(self, mock_send_email):
        """Test email sending with error."""
        # Configure mock to raise exception
        mock_send_email.side_effect = Exception("Test error")
        
        test_data = {
            'summary': 'Test summary',
            'participants': ['test@example.com']
        }
        
        response = self.app.post('/send_email', json=test_data)
        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.json['status'], 'error')

if __name__ == '__main__':
    unittest.main() 