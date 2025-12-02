import schedule # pyright: ignore[reportMissingImports]
import time
import os
from modules.crawler import YouTubeCrawler
from modules.audio_processor import AudioSplitter

# CẤU HÌNH TỪ KHÓA
KEYWORDS = [
    "Họp báo",
    "Tin tức thời sự VTV",
    "Talkshow",
    "Hội thảo",
    "Meeting",
    "Cuộc họp",
]

def job():
    print("\nBẮT ĐẦU QUÉT DATA...")
    
    # Lưu file gốc vào output/raw, file cắt vào output/dataset
    crawler = YouTubeCrawler(output_dir="/app/output/raw")
    splitter = AudioSplitter(output_dir="/app/output/dataset")

    for kw in KEYWORDS:
        # Mỗi từ khóa tìm tải 2 video mới nhất
        videos = crawler.search_and_download(kw, limit=10)
        
        for vid in videos:
            # Cắt thành các đoạn 30s
            success = splitter.split_fixed_length(vid['path'], duration_sec=30)
            
            # Nếu cắt thành công thì xóa file gốc cho nhẹ ổ cứng
            if success and os.path.exists(vid['path']):
                print(f"Đang xóa file gốc để tiết kiệm dung lượng...")
                os.remove(vid['path'])

    print("💤 HOÀN THÀNH. Ngủ đợi lần sau...")

if __name__ == "__main__":
    print("AUDIO MINER BOT ĐÃ KHỞI ĐỘNG!")
    
    # Chạy ngay 1 lần đầu
    job()
    
    # Lên lịch chạy mỗi ngày lúc 2h sáng
    schedule.every().day.at("00:00").do(job)
    
    while True:
        schedule.run_pending()
        time.sleep(60)