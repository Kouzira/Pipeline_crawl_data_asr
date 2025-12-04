import sqlite3
import os
from datetime import datetime

class DatabaseManager:
    def __init__(self, db_path="/app/data/metadata.db"):
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.cursor = self.conn.cursor()
        self.conn.execute("PRAGMA journal_mode=WAL;")
        self.create_tables()

    def create_tables(self):
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS videos (
                video_id TEXT PRIMARY KEY,
                title TEXT,
                url TEXT,
                duration INTEGER,
                downloaded_at DATETIME,
                status TEXT
            )
        ''')
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS chunks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                video_id TEXT,
                file_path TEXT,
                created_at DATETIME,
                FOREIGN KEY(video_id) REFERENCES videos(video_id)
            )
        ''')
        self.conn.commit()

    def video_exists(self, video_id):
        self.cursor.execute("SELECT 1 FROM videos WHERE video_id = ?", (video_id,))
        return self.cursor.fetchone() is not None

    def add_video(self, video_id, title, url):
        try:
            self.cursor.execute('''
                INSERT INTO videos (video_id, title, url, downloaded_at, status)
                VALUES (?, ?, ?, ?, ?)
            ''', (video_id, title, url, datetime.now(), "DOWNLOADED"))
            self.conn.commit()
            print(f"[DB] Đã lưu video: {title}")
        except sqlite3.IntegrityError:
            pass

    def add_chunks(self, video_id, chunk_paths):
        data = [(video_id, path, datetime.now()) for path in chunk_paths]
        self.cursor.executemany('''
            INSERT INTO chunks (video_id, file_path, created_at)
            VALUES (?, ?, ?)
        ''', data)
        self.cursor.execute("UPDATE videos SET status = 'SPLITTED' WHERE video_id = ?", (video_id,))
        self.conn.commit()
        print(f"[DB] Đã lưu {len(chunk_paths)} segments vào DB.")

    def close(self):
        self.conn.close()