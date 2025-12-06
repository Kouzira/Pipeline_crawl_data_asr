import time
import json
import os
import redis # pyright: ignore[reportMissingImports]
import logging
from modules.audio_processor import VADSplitter
from modules.database import DatabaseManager
from config import Config

logger = logging.getLogger("Worker_Splitter")

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

def start_worker():
    logger.info("WORKER (SPLITTER) SERVICE STARTED...")
    redis_client = connect_redis()
    db = DatabaseManager(db_path=Config.DB_PATH)
    splitter = VADSplitter(output_dir=Config.OUTPUT_DATASET)
    
    total_processed_count = 0
    has_active_work_session = False

    while True:
        try:
            task_raw = redis_client.blpop(Config.QUEUE_NAME, timeout=5)
            
            if not task_raw:
                if has_active_work_session:
                    logger.info("SPLITTER QUEUE EMPTY! Waiting for new videos...")
                    has_active_work_session = False
                continue

            has_active_work_session = True
            _, data = task_raw
            task = json.loads(data)
            video_id = task.get('video_id', 'unknown')
            file_path = task.get('file_path')
            title = task.get('title', 'No Title')
            
            logger.info(f"Processing Video: {title}")

            if not file_path or not os.path.exists(file_path):
                logger.error(f"File missing: {file_path}")
                continue

            # 1. Cắt File (VAD)
            chunks_data = splitter.process_file(file_path, video_id)
            
            if chunks_data:
                db.add_chunks(video_id, chunks_data)
                logger.info(f"   -> Created {len(chunks_data)} segments.")
                
                # 2. [THAY ĐỔI LỚN] Đẩy từng file nhỏ vào Queue Labeler
                # Thay vì đẩy cả folder, ta đẩy từng file
                count_pushed = 0
                for chunk in chunks_data:
                    label_task = {
                        "video_id": video_id,
                        "file_path": chunk['path'], # Đường dẫn file con
                        "filename": os.path.basename(chunk['path'])
                    }
                    redis_client.rpush(Config.LABELING_QUEUE_NAME, json.dumps(label_task))
                    count_pushed += 1
                
                logger.info(f"   -> Pushed {count_pushed} tasks to Labeler Queue")

                # 3. Cleanup file gốc
                try:
                    os.remove(file_path)
                except OSError: pass
            else:
                logger.warning(f"   -> No speech found for {video_id}")
                if os.path.exists(file_path): os.remove(file_path)

            total_processed_count += 1
            logger.info(f"[SPLIT DONE]: {title}")
            logger.info("-" * 50)

        except Exception as e:
            logger.error(f"Worker Error: {e}", exc_info=True)
            time.sleep(1)

if __name__ == "__main__":
    time.sleep(2)
    start_worker()