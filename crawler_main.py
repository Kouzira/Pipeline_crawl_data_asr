import schedule
import time
import sys
import os
from modules.crawler import YouTubeCrawler
from modules.database import DatabaseManager

# Danh sách từ khóa cần tìm kiếm
KEYWORDS = ["Tin tức VTV24", "Podcast tiếng Việt"]

def job():
    print("\n[CRAWLER] --- BẮT ĐẦU CHU KỲ TẢI MỚI ---")
    
    # 1. Chờ Redis khởi động (Quan trọng vì YouTubeCrawler sẽ kết nối Redis ngay khi init)
    print("[CRAWLER] Đang chờ Redis/Database sẵn sàng...")
    time.sleep(5) 
    
    # 2. Khởi tạo Database Manager
    # Lưu ý: Đảm bảo path này khớp với volume trong docker-compose
    db_path = "/app/data/metadata.db"
    db = DatabaseManager(db_path=db_path)
    
    try:
        # 3. Khởi tạo Crawler
        # class YouTubeCrawler mới của bạn đã tự init Redis bên trong
        crawler = YouTubeCrawler(db_manager=db, output_dir="/app/output/raw")
        
        # 4. Chạy vòng lặp qua từng từ khóa
        for kw in KEYWORDS:
            try:
                # Gọi hàm search_and_download với limit=2 như yêu cầu
                crawler.search_and_download(keyword=kw, limit=2)
            except Exception as e_inner:
                print(f"[CRAWLER] Lỗi khi xử lý từ khóa '{kw}': {e_inner}")
                
    except Exception as e:
        print(f"[CRAWLER] Lỗi nghiêm trọng trong quá trình chạy Job: {e}")
        
    finally:
        # 5. Luôn đóng kết nối Database để tránh lỗi "Database is locked"
        if 'db' in locals():
            db.close()
        print("[CRAWLER] Kết thúc chu kỳ. Ngủ đợi lần sau...")
        # Flush stdout để log hiện ngay lập tức trong Docker
        sys.stdout.flush()

if __name__ == "__main__":
    print("[SYSTEM] CRAWLER SERVICE STARTED")
    
    # Chạy ngay một lần khi container vừa khởi động
    job()
    
    # Lên lịch chạy vào 00:00 hàng ngày
    schedule.every().day.at("00:00").do(job)
    
    # Vòng lặp vô tận để giữ container sống
    while True:
        schedule.run_pending()
        time.sleep(60)