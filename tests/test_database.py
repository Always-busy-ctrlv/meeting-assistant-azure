import os
import unittest
import sqlite3
import tempfile
import shutil
from database import init_db, save_meeting, update_meeting_participants, get_all_meetings

class TestDatabase(unittest.TestCase):
    def setUp(self):
        # Create a temporary directory for the test database
        self.test_dir = tempfile.mkdtemp()
        self.test_db_path = os.path.join(self.test_dir, 'test_meetings.db')
        # Initialize the test database
        init_db(self.test_db_path)

    def tearDown(self):
        # Clean up the temporary directory and its contents
        shutil.rmtree(self.test_dir)

    def test_init_db(self):
        """Test database initialization."""
        # Check if database file exists
        self.assertTrue(os.path.exists(self.test_db_path))
        
        # Verify table structure
        conn = sqlite3.connect(self.test_db_path)
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(meetings)")
        columns = {row[1]: row[2] for row in cursor.fetchall()}
        conn.close()
        
        # Verify required columns exist
        self.assertIn('id', columns)
        self.assertIn('timestamp', columns)
        self.assertIn('transcript', columns)
        self.assertIn('summary', columns)
        self.assertIn('participants', columns)

    def test_save_meeting(self):
        """Test saving a meeting."""
        # Test data
        transcript = "Test transcript"
        summary = "Test summary"

        # Save meeting
        meeting_id = save_meeting(transcript, summary, self.test_db_path)

        # Verify saved data
        conn = sqlite3.connect(self.test_db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM meetings WHERE id = ?", (meeting_id,))
        row = cursor.fetchone()
        conn.close()

        self.assertIsNotNone(row)
        self.assertEqual(row[2], transcript)
        self.assertEqual(row[3], summary)
        self.assertIsNone(row[4])  # participants should be None initially

    def test_update_meeting_participants(self):
        """Test updating meeting participants."""
        # First save a meeting
        meeting_id = save_meeting("Test transcript", "Test summary", self.test_db_path)

        # Test participants
        participants = ["test1@example.com", "test2@example.com"]

        # Update participants
        update_meeting_participants(participants, self.test_db_path)

        # Verify update
        conn = sqlite3.connect(self.test_db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT participants FROM meetings WHERE id = ?", (meeting_id,))
        result = cursor.fetchone()
        conn.close()

        self.assertIsNotNone(result)
        self.assertEqual(result[0], ",".join(participants))

    def test_get_all_meetings(self):
        """Test retrieving all meetings."""
        # Save multiple meetings
        save_meeting("Transcript 1", "Summary 1", self.test_db_path)
        save_meeting("Transcript 2", "Summary 2", self.test_db_path)

        # Get all meetings
        meetings = get_all_meetings(self.test_db_path)

        # Verify results
        self.assertEqual(len(meetings), 2)
        self.assertEqual(meetings[0]['transcript'], "Transcript 2")  # Most recent first
        self.assertEqual(meetings[1]['transcript'], "Transcript 1")

if __name__ == '__main__':
    unittest.main() 