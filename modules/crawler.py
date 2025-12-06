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

    def _is_relevant(self, entry, keyword):
        """Kiểm tra độ liên quan của video với từ khóa."""
        if not entry: return False
        
        title = entry.get('title', '').lower()
        channel = entry.get('uploader', '').lower()
        kw_lower = keyword.lower()

        # 1. Khớp chính xác
        if kw_lower in title or kw_lower in channel:
            return True

        # 2. Khớp theo từ (Word Overlap > 60%)
        kw_words = set(kw_lower.split())
        target_words = set(title.split() + channel.split())
        
        common_words = kw_words.intersection(target_words)
        match_ratio = len(common_words) / len(kw_words) if len(kw_words) > 0 else 0
        
        if match_ratio >= 0.6:
            return True
            
        logger.info(f"[SKIP] Irrelevant content: '{title}' (Match: {match_ratio:.2f})")
        return False

    def search_and_download(self, keyword, limit=Config.SEARCH_LIMIT):
        """
        Trả về: (int) Số lượng video tải thành công
        """
        logger.info(f"[SEARCH] Keyword: '{keyword}' (Target: {limit} new videos)...")

        # --- CHIẾN THUẬT DEEP SEARCH ---
        # Lấy danh sách 500 kết quả metadata để "đào" qua các video đã tải.
        # extract_flat=True chỉ lấy text nên 500 hay 1000 items cũng rất nhanh.
        search_buffer = 500
        
        ydl_opts_search = {
            'quiet': True,
            'ignoreerrors': True,
            'extract_flat': True, 
            'cookiefile': Config.COOKIE_FILE if os.path.exists(Config.COOKIE_FILE) else None,
            'default_search': f'ytsearch{search_buffer}',
        }

        video_list = []
        skipped_count = 0
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts_search) as ydl:
                info = ydl.extract_info(f"ytsearch{search_buffer}:{keyword}", download=False)
                
                if 'entries' in info:
                    for entry in info['entries']:
                        if not entry: continue
                        
                        video_id = entry['id']
                        title = entry.get('title', 'No Title')

                        # 1. KIỂM TRA DATABASE (QUAN TRỌNG)
                        # Nếu đã có -> Bỏ qua -> Tiếp tục đào xuống video cũ hơn
                        if self.db.video_exists(video_id):
                            skipped_count += 1
                            continue
                            
                        # 2. Kiểm tra độ liên quan
                        if self._is_relevant(entry, keyword):
                            video_list.append(entry)
                        
                        # Nếu đã gom đủ số lượng video MỚI cần thiết thì dừng lại
                        if len(video_list) >= limit:
                            break
                            
        except Exception as e:
            logger.error(f"[ERROR] Search failed: {e}")
            return 0

        if skipped_count > 0:
            logger.info(f"[INFO] Skipped {skipped_count} existing videos from DB to find new ones.")

        if not video_list:
            logger.info(f"[INFO] No valid NEW videos found for '{keyword}' after checking {search_buffer} results.")
            return 0

        logger.info(f"[INFO] Found {len(video_list)} new videos (Deep Search). Starting download...")

        success_count = 0 
        with ThreadPoolExecutor(max_workers=Config.MAX_WORKERS) as executor:
            future_to_video = {
                executor.submit(self._download_worker, video): video 
                for video in video_list
            }
            
            for future in as_completed(future_to_video):
                try:
                    future.result()
                    success_count += 1
                except Exception as exc:
                    logger.error(f"[ERROR] Download task failed: {exc}")
        
        return success_count

    def _download_worker(self, entry):
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
            logger.error(f"[FAIL] Download error for '{title}': {e}")
            raise e