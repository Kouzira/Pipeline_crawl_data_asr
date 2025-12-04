import yt_dlp
import json
import redis
import os
import random
import time

class YouTubeCrawler:
    def __init__(self, db_manager, output_dir="/app/output/raw"):
        self.db = db_manager
        self.output_dir = output_dir
        self.redis_client = redis.Redis(host='redis', port=6379, db=0)
        self.cookie_file = "/app/data/cookies.txt"
        os.makedirs(output_dir, exist_ok=True)

    def search_and_download(self, keyword, limit=2):
        print(f"[CRAWLER] Tìm: '{keyword}'...")

        ydl_opts = {
            'format': 'bestaudio/best', # Chỉ tải audio
            'outtmpl': f'{self.output_dir}/%(id)s.%(ext)s',
            
            # --- PRE-PROCESSING CHO ASR ---
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'wav',
            }],
            'postprocessor_args': [
                '-ac', '1',       # Mono
                '-ar', '16000'    # 16kHz
            ],
            
            # --- ANTI-BAN ---
            'cookiefile': self.cookie_file if os.path.exists(self.cookie_file) else None,
            'sleep_interval': 5,
            'max_sleep_interval': 15,
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            
            'quiet': True,
            'ignoreerrors': True,
            'default_search': f'ytsearch{limit}',
        }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(f"ytsearch{limit}:{keyword}", download=True)
                
                if 'entries' in info:
                    for entry in info['entries']:
                        if not entry: continue
                        
                        vid = entry['id']
                        title = entry['title']
                        
                        # Chỉ add task nếu chưa có trong DB
                        if not self.db.video_exists(vid):
                            self.db.add_video(vid, title, entry['webpage_url'])
                            
                            # File path sau khi ffmpeg convert sẽ là .wav
                            final_path = f"{self.output_dir}/{vid}.wav"
                            
                            task = {
                                "video_id": vid,
                                "file_path": final_path,
                                "title": title
                            }
                            self.redis_client.rpush('audio_tasks', json.dumps(task))
                            print(f"[QUEUE] + {title}")
                            time.sleep(random.randint(2, 5))
                        else:
                            print(f"[SKIP] Đã có: {title}")

        except Exception as e:
            print(f"[ERROR] {e}")