import yt_dlp # pyright: ignore[reportMissingModuleSource]
import json
import redis # pyright: ignore[reportMissingImports]
import os
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from config import Config

logger = logging.getLogger("Crawler_Core")

class YouTubeCrawler:
    def __init__(self, db_manager, output_dir=Config.OUTPUT_RAW):
        self.db = db_manager
        self.output_dir = output_dir
        self.redis_client = redis.Redis(
            host=Config.REDIS_HOST, 
            port=Config.REDIS_PORT, 
            db=0
        )
        os.makedirs(output_dir, exist_ok=True)

    def search_and_download(self, keyword, limit=Config.SEARCH_LIMIT):
        """
        Trả về: (int) Số lượng video tải thành công
        """
        logger.info(f"Searching for: '{keyword}' (Limit: {limit})...")

        ydl_opts_search = {
            'quiet': True,
            'ignoreerrors': True,
            'extract_flat': True,
            'cookiefile': Config.COOKIE_FILE if os.path.exists(Config.COOKIE_FILE) else None,
            'default_search': f'ytsearch{limit}',
        }

        video_list = []
        try:
            with yt_dlp.YoutubeDL(ydl_opts_search) as ydl:
                info = ydl.extract_info(f"ytsearch{limit}:{keyword}", download=False)
                if 'entries' in info:
                    for entry in info['entries']:
                        if entry and not self.db.video_exists(entry['id']):
                            video_list.append(entry)
        except Exception as e:
            logger.error(f"Search error: {e}")
            return 0 # Trả về 0 nếu lỗi tìm kiếm

        if not video_list:
            logger.info(f"No new videos found for '{keyword}'.")
            return 0 # Trả về 0 nếu không có video mới

        logger.info(f"Found {len(video_list)} new videos. Starting parallel download...")

        # Biến đếm số lượng thành công
        success_count = 0 

        with ThreadPoolExecutor(max_workers=Config.MAX_WORKERS) as executor:
            future_to_video = {
                executor.submit(self._download_worker, video): video 
                for video in video_list
            }
            
            for future in as_completed(future_to_video):
                try:
                    future.result()
                    # Nếu không văng lỗi thì tính là thành công
                    success_count += 1
                except Exception as exc:
                    logger.error(f"Download task failed: {exc}")
        
        return success_count # Trả về tổng số tải được

    def _download_worker(self, entry):
        # ... (Phần này giữ nguyên y hệt cũ) ...
        video_id = entry['id']
        title = entry.get('title', 'No Title')
        url = entry.get('url', f"https://www.youtube.com/watch?v={video_id}")
        
        ydl_opts_down = {
            'format': 'bestaudio/best',
            'outtmpl': f'{self.output_dir}/%(id)s.%(ext)s',
            'postprocessors': [{'key': 'FFmpegExtractAudio','preferredcodec': 'wav'}],
            'postprocessor_args': ['-ac', '1', '-ar', str(Config.SAMPLE_RATE)],
            'cookiefile': Config.COOKIE_FILE if os.path.exists(Config.COOKIE_FILE) else None,
            'quiet': True,
            'no_warnings': True,
            'sleep_interval': 1, 
            'max_sleep_interval': 3,
        }

        try:
            with yt_dlp.YoutubeDL(ydl_opts_down) as ydl:
                ydl.download([url])
            
            self.db.add_video(video_id, title, url)
            
            final_path = f"{self.output_dir}/{video_id}.wav"
            task = {"video_id": video_id, "file_path": final_path, "title": title}
            
            self.redis_client.rpush(Config.QUEUE_NAME, json.dumps(task))
            logger.info(f"[DONE] Downloaded & Queued: {title}")
            
        except Exception as e:
            logger.error(f"[FAIL] Download worker error {title}: {e}")
            raise e