import time
import json
import os
import redis # pyright: ignore[reportMissingImports]
import logging
from modules.audio_processor import VADSplitter
from modules.database import DatabaseManager
from config import Config

logger = logging.getLogger("Worker_Main")

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
    logger.info("WORKER SERVICE STARTED...")
    redis_client = connect_redis()
    db = DatabaseManager(db_path=Config.DB_PATH)
    splitter = VADSplitter(output_dir=Config.OUTPUT_DATASET)
    
    total_processed_count = 0
    
    # [LOGIC MỚI] Biến theo dõi trạng thái làm việc
    # True: Vừa mới làm xong task, đang chờ task tiếp theo
    # False: Đang rảnh rỗi từ lâu rồi
    has_active_work_session = False

    while True:
        try:
            # Giảm timeout xuống 5s để phản hồi nhanh hơn khi hết việc
            task_raw = redis_client.blpop(Config.QUEUE_NAME, timeout=5)
            
            # --- TRƯỜNG HỢP 1: KHÔNG CÓ TASK (TIMEOUT) ---
            if not task_raw:
                # Nếu trước đó đang làm việc (has_active_work_session = True)
                # Mà giờ lại timeout -> Nghĩa là vừa làm xong task cuối cùng
                if has_active_work_session:
                    logger.info("Completed All Task")
                    logger.info("Standing by for new tasks...")
                    # Reset trạng thái để không in thông báo này liên tục
                    has_active_work_session = False
                
                # Tiếp tục vòng lặp chờ đợi
                continue

            # --- TRƯỜNG HỢP 2: CÓ TASK MỚI ---
            # Đánh dấu là đang trong phiên làm việc
            has_active_work_session = True
            
            _, data = task_raw
            task = json.loads(data)
            video_id = task.get('video_id', 'unknown')
            file_path = task.get('file_path')
            title = task.get('title', 'No Title')
            
            logger.info(f"Processing Task: {title}")

            if not file_path or not os.path.exists(file_path):
                logger.error(f"File missing: {file_path}")
                continue

            chunks_data = splitter.process_file(file_path, video_id)
            
            if chunks_data:
                db.add_chunks(video_id, chunks_data)
                logger.info(f"   -> Created {len(chunks_data)} segments.")
                try:
                    os.remove(file_path)
                    logger.info(f"   -> Deleted raw file: {file_path}")
                except OSError: pass
            else:
                logger.warning(f"   -> No speech found or Error processing {video_id}")
                if os.path.exists(file_path): os.remove(file_path)

            total_processed_count += 1
            logger.info(f"[COMPLETED] Finished: {title} (Session Total: {total_processed_count})")
            logger.info("-" * 50)

        except Exception as e:
            logger.error(f"Worker Error: {e}", exc_info=True)
            if 'data' in locals():
                redis_client.rpush(Config.FAILED_QUEUE_NAME, data)
            time.sleep(1)

if __name__ == "__main__":
    time.sleep(2)
    start_worker()