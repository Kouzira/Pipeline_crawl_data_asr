import schedule # pyright: ignore[reportMissingImports]
import time
import sys
import os
import glob
import logging
from modules.crawler import YouTubeCrawler
from modules.database import DatabaseManager
from config import Config

logger = logging.getLogger("Crawler_Main")

def clean_zombie_files():
    # ... (Giữ nguyên logic cũ) ...
    logger.info("Maintenance: Scanning for zombie files...")
    now = time.time()
    cutoff = now - (24 * 3600)
    files = glob.glob(os.path.join(Config.OUTPUT_RAW, "*.wav"))
    count = 0
    for f in files:
        try:
            if os.stat(f).st_mtime < cutoff:
                os.remove(f)
                count += 1
        except Exception: pass
    if count > 0: logger.info(f"Cleaned {count} zombie files.")

def job():
    logger.info("--- STARTING CRAWL CYCLE ---")
    clean_zombie_files()
    
    db = DatabaseManager(db_path=Config.DB_PATH)
    total_downloaded_session = 0 # Biến đếm tổng số tải được trong phiên này

    try:
        crawler = YouTubeCrawler(db_manager=db, output_dir=Config.OUTPUT_RAW)
        
        for kw in Config.KEYWORDS:
            logger.info(f"Processing keyword: {kw}")
            
            # Nhận số lượng tải thành công từ hàm search_and_download
            count = crawler.search_and_download(keyword=kw, limit=Config.SEARCH_LIMIT)
            
            # Cộng dồn
            total_downloaded_session += count
                
    except Exception as e:
        logger.error(f"Job Critical Error: {e}", exc_info=True)
        
    finally:
        db.close()
        logger.info("Cycle finished. Sleeping...")
        
        # In ra tổng số đã tải được (Chính xác 100% dù Worker đã xóa file hay chưa)
        logger.info(f"REPORT: Total videos downloaded in this session: {total_downloaded_session}")
        
        sys.stdout.flush()

if __name__ == "__main__":
    logger.info("SYSTEM STARTED - CRAWLER SERVICE")
    time.sleep(5)
    job()
    schedule.every().day.at("00:00").do(job)
    while True:
        schedule.run_pending()
        time.sleep(60)