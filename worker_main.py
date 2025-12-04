import time
import json
import os
import redis
from modules.audio_processor import VADSplitter
from modules.database import DatabaseManager

def start_worker():
    print("WORKER SERVICE STARTED (VAD ENABLED)...")
    
    redis_client = redis.Redis(host='redis', port=6379, db=0)
    db = DatabaseManager(db_path="/app/data/metadata.db")
    splitter = VADSplitter(output_dir="/app/output/dataset")

    while True:
        try:
            # Lấy task từ Redis
            _, data = redis_client.blpop('audio_tasks', timeout=0)
            task = json.loads(data)
            
            print(f"[WORKER] Xử lý: {task['title']}")
            
            # Cắt file
            chunks_data = splitter.process_file(task['file_path'], task['video_id'])
            
            if chunks_data:
                db.add_chunks(task['video_id'], chunks_data)
                print(f"[WORKER] -> Tạo {len(chunks_data)} segments.")
                
                # Xóa file gốc để giải phóng dung lượng
                if os.path.exists(task['file_path']):
                    os.remove(task['file_path'])
            else:
                print("[WORKER] File không có giọng nói hoặc lỗi.")

        except Exception as e:
            print(f"[WORKER ERROR] {e}")
            time.sleep(1)

if __name__ == "__main__":
    time.sleep(5)
    start_worker()