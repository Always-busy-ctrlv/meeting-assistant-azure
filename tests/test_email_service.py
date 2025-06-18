import unittest
from unittest.mock import patch, MagicMock
from email_service import send_meeting_summary
from config import EMAIL_USER, EMAIL_PASSWORD, EMAIL_SMTP_SERVER, EMAIL_SMTP_PORT

class TestEmailService(unittest.TestCase):
    def setUp(self):
        # Test data
        self.test_participants = ["test1@example.com", "test2@example.com"]
        self.test_summary = "Test meeting summary"

    @patch('smtplib.SMTP')
    def test_send_meeting_summary_success(self, mock_smtp):
        # Configure mock
        mock_smtp_instance = MagicMock()
        mock_smtp.return_value.__enter__.return_value = mock_smtp_instance
        
        # Send email
        success, message = send_meeting_summary(self.test_participants, self.test_summary)
        
        # Verify results
        self.assertTrue(success)
        self.assertEqual(message, "Email sent successfully")
        
        # Verify SMTP calls
        mock_smtp.assert_called_once_with(EMAIL_SMTP_SERVER, int(EMAIL_SMTP_PORT))
        mock_smtp_instance.starttls.assert_called_once()
        mock_smtp_instance.login.assert_called_once_with(EMAIL_USER, EMAIL_PASSWORD)
        mock_smtp_instance.send_message.assert_called_once()

    @patch('smtplib.SMTP')
    def test_send_meeting_summary_smtp_error(self, mock_smtp):
        # Configure mock to raise exception
        mock_smtp.return_value.__enter__.side_effect = Exception("SMTP Error")
        
        # Send email
        success, message = send_meeting_summary(self.test_participants, self.test_summary)
        
        # Verify results
        self.assertFalse(success)
        self.assertEqual(message, "Failed to send email: SMTP Error")

    def test_send_meeting_summary_empty_participants(self):
        # Test with empty participants list
        success, message = send_meeting_summary([], self.test_summary)
        
        # Verify results
        self.assertFalse(success)
        self.assertEqual(message, "No recipients specified")

    def test_send_meeting_summary_empty_summary(self):
        # Test with empty summary
        success, message = send_meeting_summary(self.test_participants, "")
        
        # Verify results
        self.assertFalse(success)
        self.assertEqual(message, "No summary content provided")

if __name__ == '__main__':
    unittest.main() 