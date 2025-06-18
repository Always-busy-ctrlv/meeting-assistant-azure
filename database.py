import sqlite3
import datetime
import json
import os
from pathlib import Path

# Use a local SQLite database
DATABASE_PATH = 'meetings.db'

def get_connection():
    """Get a connection to the SQLite database."""
    return sqlite3.connect(DATABASE_PATH)

def init_db():
    """Initialize the SQLite database."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS meetings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME NOT NULL,
                transcript TEXT NOT NULL,
                summary TEXT NOT NULL,
                participants TEXT
            )
        ''')
        conn.commit()
        conn.close()
        print("Database initialized successfully")
    except Exception as e:
        print(f"Error initializing database: {str(e)}")
        raise e

def save_meeting(transcript, summary):
    """Save a meeting's transcript and summary to the database."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        timestamp = datetime.datetime.now()
        cursor.execute(
            "INSERT INTO meetings (timestamp, transcript, summary) VALUES (?, ?, ?)",
            (timestamp, transcript, summary)
        )
        conn.commit()
        meeting_id = cursor.lastrowid
        conn.close()
        return meeting_id
    except Exception as e:
        print(f"Error saving meeting: {str(e)}")
        if conn:
            conn.close()
        raise e

def update_meeting_participants(participants):
    """Update the most recent meeting with participant information."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM meetings ORDER BY id DESC LIMIT 1")
        result = cursor.fetchone()
        if result:
            meeting_id = result[0]
            participants_str = ",".join(participants)
            cursor.execute(
                "UPDATE meetings SET participants = ? WHERE id = ?",
                (participants_str, meeting_id)
            )
            conn.commit()
        else:
            print("No meetings found to update participants")
        conn.close()
    except Exception as e:
        print(f"Error updating participants: {str(e)}")
        if conn:
            conn.close()
        raise e

def get_all_meetings():
    """Get all meetings from the database."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM meetings ORDER BY timestamp DESC")
        meetings = []
        for row in cursor.fetchall():
            meetings.append({
                'id': row[0],
                'timestamp': row[1],
                'transcript': row[2],
                'summary': row[3],
                'participants': row[4].split(',') if row[4] else []
            })
        conn.close()
        return meetings
    except Exception as e:
        print(f"Error getting meetings: {str(e)}")
        if conn:
            conn.close()
        raise e 