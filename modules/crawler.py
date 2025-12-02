import os
import time
import yt_dlp
from playwright.sync_api import sync_playwright

class YouTubeCrawler:
    def __init__(self, output_dir="/app/output/raw", history_file="/app/data/history.txt"):
        self.output_dir = output_dir
        self.history_file = history_file
        self.cookie_file = "/app/data/youtube_cookies.txt"
        
        # User Agent thống nhất cho cả Playwright và yt-dlp (RẤT QUAN TRỌNG)
        self.user_agent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36'
        
        os.makedirs(output_dir, exist_ok=True)
        os.makedirs(os.path.dirname(history_file), exist_ok=True)
        
        if not os.path.exists(history_file):
            with open(history_file, 'w') as f: f.write("")

    def _is_downloaded(self, video_id):
        with open(self.history_file, 'r') as f:
            return video_id in f.read().splitlines()

    def _mark_downloaded(self, video_id):
        with open(self.history_file, 'a') as f:
            f.write(f"{video_id}\n")

    def search_and_download(self, keyword, limit=2):
        print(f"Playwright đang khởi động để tìm: '{keyword}'...")
        downloaded_files = []

        with sync_playwright() as p:
            # 1. MỞ TRÌNH DUYỆT (Dùng User-Agent cố định)
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(user_agent=self.user_agent)
            page = context.new_page()

            try:
                # 2. VÀO YOUTUBE
                search_url = f"https://www.youtube.com/results?search_query={keyword.replace(' ', '+')}&sp=EgIYAg%253D%253D"
                page.goto(search_url, timeout=60000)
                
                # Chờ load phần tử video
                page.wait_for_selector('ytd-video-renderer', timeout=15000)
                time.sleep(3) # Chờ thêm chút để Cookies ổn định

                # 3. LẤY VÀ LƯU COOKIES (Đã fix lỗi -1)
                cookies = context.cookies()
                self._save_cookies_netscape(cookies)
                
                # 4. LẤY LINK VIDEO
                video_elements = page.query_selector_all('a#video-title')
                candidates = []
                for vid in video_elements:
                    url = vid.get_attribute('href')
                    title = vid.get_attribute('title')
                    if url and '/watch?v=' in url:
                        v_id = url.split('v=')[1].split('&')[0]
                        if not self._is_downloaded(v_id):
                            candidates.append({'id': v_id, 'title': title, 'url': f"https://www.youtube.com{url}"})
                            if len(candidates) >= limit: break
                
                print(f"Tìm thấy {len(candidates)} video mới. Đã cập nhật Cookies.")

            except Exception as e:
                print(f"Lỗi Playwright: {e}")
                browser.close()
                return []
            
            browser.close()

            # 5. TẢI BẰNG YT-DLP
            for item in candidates:
                print(f"\nĐang tải: {item['title']}...\n")
                if self._download_with_ffmpeg(item['url'], item['id']):
                    downloaded_files.append({'path': f"{self.output_dir}/{item['id']}.wav", 'title': item['title']})
        
        return downloaded_files

    def _save_cookies_netscape(self, cookies):
        """
        FIX LỖI QUAN TRỌNG: 
        Xử lý trường hợp 'expires' = -1 (Session Cookie) mà yt-dlp không hiểu.
        Chuyển -1 thành 0.
        """
        with open(self.cookie_file, 'w') as f:
            f.write("# Netscape HTTP Cookie File\n")
            for c in cookies:
                domain = c['domain']
                flag = 'TRUE' if domain.startswith('.') else 'FALSE'
                path = c['path']
                secure = 'TRUE' if c['secure'] else 'FALSE'
                
                # --- ĐOẠN FIX LỖI ---
                expires = c.get('expires', 0)
                if expires == -1:
                    expires = 0 # Đổi -1 thành 0 (Session Cookie chuẩn Netscape)
                expiration = str(int(expires))
                # --------------------

                name = c['name']
                value = c['value']
                f.write(f"{domain}\t{flag}\t{path}\t{secure}\t{expiration}\t{name}\t{value}\n")

    def _download_with_ffmpeg(self, url, video_id):
        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': f'{self.output_dir}/%(id)s.%(ext)s',
            'postprocessors': [{'key': 'FFmpegExtractAudio','preferredcodec': 'wav'}],
            'noplaylist': True,
            'quiet': True,
            'no_warnings': True,
            'cookiefile': self.cookie_file,
            'http_headers': {
                'User-Agent': self.user_agent # Dùng chung User-Agent với Playwright
            },
            # Thêm dòng này để ép dùng IPv4 (Tránh bị chặn IP Server)
            'force_ipv4': True 
        }
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
                self._mark_downloaded(video_id)
                return True
        except Exception as e:
            print(f"Vẫn lỗi 403? YouTube đang chặn gắt. Chi tiết: {e}")
            return False