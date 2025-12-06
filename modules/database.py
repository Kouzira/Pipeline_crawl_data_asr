import sqlite3
import os
import logging
from datetime import datetime
from config import Config

logger = logging.getLogger("Database")

class DatabaseManager:
    def __init__(self, db_path=Config.DB_PATH):
        self.db_path = db_path
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.cursor = self.conn.cursor()
        self.conn.execute("PRAGMA journal_mode=WAL;")
        self.create_tables()

    def create_tables(self):
        try:
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS videos (
                    video_id TEXT PRIMARY KEY,
                    title TEXT,
                    url TEXT,
                    downloaded_at DATETIME
                )
            ''')
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS chunks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    video_id TEXT,
                    file_path TEXT,
                    duration REAL, 
                    transcript TEXT, 
                    created_at DATETIME,
                    FOREIGN KEY(video_id) REFERENCES videos(video_id)
                )
            ''')
            self.conn.commit()
        except Exception as e:
            logger.error(f"Error creating tables: {e}")

    def video_exists(self, video_id):
        try:
            self.cursor.execute("SELECT 1 FROM videos WHERE video_id = ?", (video_id,))
            return self.cursor.fetchone() is not None
        except Exception:
            return False

    def add_video(self, video_id, title, url):
        try:
            self.cursor.execute('INSERT INTO videos VALUES (?, ?, ?, ?)', 
                                (video_id, title, url, datetime.now()))
            self.conn.commit()
        except sqlite3.IntegrityError:
            pass
        except Exception as e:
            logger.error(f"Error adding video {video_id}: {e}")

    def add_chunks(self, video_id, chunks_data):
        try:
            data = [(video_id, c['path'], c['duration'], datetime.now()) for c in chunks_data]
            self.cursor.executemany('''
                INSERT INTO chunks (video_id, file_path, duration, created_at)
                VALUES (?, ?, ?, ?)
            ''', data)
            self.conn.commit()
        except Exception as e:
            logger.error(f"Error adding chunks for {video_id}: {e}")

    def close(self):
        self.conn.close()