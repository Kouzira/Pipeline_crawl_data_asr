import time
import json
import os
import redis
from modules.audio_processor import AudioSplitter
from modules.database import DatabaseManager

def start_worker():
    print("👷 WORKER SERVICE STARTED - Đang chờ việc từ Redis...")
    
    redis_client = redis.Redis(host='redis', port=6379, db=0)
    db = DatabaseManager(db_path="/app/data/metadata.db")
    splitter = AudioSplitter(output_dir="/app/output/dataset")

    while True:
        try:
            # Chờ task (Blocking)
            _, data = redis_client.blpop('audio_tasks', timeout=0)
            
            task = json.loads(data)
            print(f"[WORKER] Nhận việc: {task['title']}")
            
            # Cắt Mềm 30s
            chunks = splitter.split_smart_30s(task['file_path'], target_sec=30)
            
            if chunks:
                db.add_chunks(task['video_id'], chunks)
                if os.path.exists(task['file_path']):
                    os.remove(task['file_path'])
                    print(f"[WORKER] Hoàn thành & Đã xóa gốc.")
            else:
                print(f"[WORKER] File lỗi.")

        except Exception as e:
            print(f"[WORKER] Lỗi: {e}")
            time.sleep(5)

if __name__ == "__main__":
    time.sleep(10)
    start_worker()