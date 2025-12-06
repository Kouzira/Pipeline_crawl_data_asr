import time
import json
import os
import redis # pyright: ignore[reportMissingImports]
import logging
from modules.labeler import GeminiLabeler
from config import Config

logger = logging.getLogger("Labeler_Service")

def connect_redis():
    while True:
        try:
            client = redis.Redis(host=Config.REDIS_HOST, port=Config.REDIS_PORT, db=0)
            client.ping()
            logger.info("Connected to Redis successfully.")
            return client
        except redis.ConnectionError:
            logger.warning("Redis unavailable, retrying in 5s...")
            time.sleep(5)

def start_labeler():
    logger.info("LABELER SERVICE STARTED (Atomic File Mode)...")
    redis_client = connect_redis()
    labeler = GeminiLabeler()
    
    if not labeler.api_ready:
        logger.error("API Key missing! Labeler service pausing...")
        while True: time.sleep(60)

    while True:
        try:
            # Lấy 1 task (1 file) từ hàng đợi
            task_raw = redis_client.blpop(Config.LABELING_QUEUE_NAME, timeout=10)
            
            if not task_raw:
                # Không làm gì cả, chỉ chờ tiếp. Log nhiều quá sẽ rác.
                continue

            _, data = task_raw
            task = json.loads(data)
            
            video_id = task.get('video_id')
            file_path = task.get('file_path')
            filename = task.get('filename')
            
            # Xử lý 1 file
            if os.path.exists(file_path):
                labeler.process_single_file(video_id, file_path, filename)
            else:
                logger.warning(f"File missing: {file_path}")

        except Exception as e:
            logger.error(f"Labeler Error: {e}", exc_info=True)
            time.sleep(1)

if __name__ == "__main__":
    time.sleep(5)
    start_labeler()