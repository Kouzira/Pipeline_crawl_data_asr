import os
import time
import json
import redis
import yt_dlp
from playwright.sync_api import sync_playwright

class YouTubeCrawler:
    def __init__(self, db_manager, output_dir="/app/output/raw"):
        self.db = db_manager
        self.output_dir = output_dir
        self.cookie_file = "/app/data/youtube_cookies.txt"
        self.user_agent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36'
        self.redis_client = redis.Redis(host='redis', port=6379, db=0)
        os.makedirs(output_dir, exist_ok=True)

    def search_and_download(self, keyword, limit=2):
        print(f"🚀 Playwright đang tìm: '{keyword}'...")
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(user_agent=self.user_agent)
            page = context.new_page()

            try:
                page.goto(f"https://www.youtube.com/results?search_query={keyword.replace(' ', '+')}&sp=EgIYAg%253D%253D", timeout=60000)
                page.wait_for_selector('ytd-video-renderer', timeout=15000)
                time.sleep(3)

                cookies = context.cookies()
                self._save_cookies_netscape(cookies)
                
                video_elements = page.query_selector_all('a#video-title')
                candidates = []
                for vid in video_elements:
                    url = vid.get_attribute('href')
                    title = vid.get_attribute('title')
                    if url and '/watch?v=' in url:
                        v_id = url.split('v=')[1].split('&')[0]
                        if not self.db.video_exists(v_id):
                            candidates.append({'id': v_id, 'title': title, 'url': f"https://www.youtube.com{url}"})
                            if len(candidates) >= limit: break
                        else:
                            print(f"⏭️ [DB] Bỏ qua: {title}")

            except Exception as e:
                print(f"❌ Lỗi Playwright: {e}")
                browser.close()
                return
            browser.close()

            for item in candidates:
                print(f"⬇️ Đang tải: {item['title']}...")
                if self._download_with_ffmpeg(item['url'], item['id']):
                    self.db.add_video(item['id'], item['title'], item['url'])
                    
                    # --- ĐẨY VÀO QUEUE ---
                    task = {
                        "video_id": item['id'],
                        "file_path": f"{self.output_dir}/{item['id']}.wav",
                        "title": item['title']
                    }
                    self.redis_client.rpush('audio_tasks', json.dumps(task))
                    print(f"📌 Đã ghim Task vào Redis: {item['title']}")

    def _save_cookies_netscape(self, cookies):
        with open(self.cookie_file, 'w') as f:
            f.write("# Netscape HTTP Cookie File\n")
            for c in cookies:
                expires = c.get('expires', 0)
                if expires == -1: expires = 0
                f.write(f"{c['domain']}\t{'TRUE' if c['domain'].startswith('.') else 'FALSE'}\t{c['path']}\t{'TRUE' if c['secure'] else 'FALSE'}\t{int(expires)}\t{c['name']}\t{c['value']}\n")

    def _download_with_ffmpeg(self, url, video_id):
        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': f'{self.output_dir}/%(id)s.%(ext)s',
            'postprocessors': [{'key': 'FFmpegExtractAudio','preferredcodec': 'wav'}],
            'noplaylist': True, 'quiet': True, 'no_warnings': True,
            'cookiefile': self.cookie_file,
            'http_headers': {'User-Agent': self.user_agent},
            'force_ipv4': True
        }
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
                return True
        except Exception:
            return False