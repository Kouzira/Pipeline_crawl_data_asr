#Auto Audio Mining Bot (YouTube Crawler & Splitter)

Dự án tự động hóa quy trình thu thập dữ liệu âm thanh từ YouTube để phục vụ huấn luyện mô hình AI (ASR/Speech-to-Text). Bot được đóng gói hoàn toàn trong Docker, có khả năng tự động tìm kiếm, tải về và cắt nhỏ file âm thanh theo định kỳ.

##Tính năng nổi bật

* **Anti-Bot Detection:** Sử dụng **Playwright** để giả lập trình duyệt thật, tự động lấy Cookies và User-Agent xịn để vượt qua lỗi chặn `403 Forbidden` của YouTube.
* **Auto Search & Download:** Tự động tìm kiếm video theo danh sách từ khóa (Keywords) được cấu hình sẵn.
* **Audio Processing:** Tự động tách Audio, chuyển đổi sang định dạng `.wav` chuẩn (sử dụng FFmpeg) và cắt thành các đoạn nhỏ (ví dụ: 30 giây).
* **Smart History:** Có cơ chế ghi nhớ các video đã tải để tránh tải trùng lặp.
* **Scheduler:** Tự động chạy theo lịch trình (ví dụ: 00:00 hàng ngày) hoặc chạy ngay lập tức.
* **Dockerized:** Chạy trên mọi môi trường (Windows/Mac/Linux/VPS) chỉ với 1 lệnh.

## Công nghệ sử dụng

* **Ngôn ngữ:** Python 3.10+
* **Core Libraries:**
    * `playwright`: Giả lập trình duyệt, lấy Cookies Netscape.
    * `yt-dlp`: Tải video/audio từ YouTube.
    * `pydub` & `ffmpeg`: Xử lý và cắt file âm thanh.
    * `schedule`: Lên lịch chạy tác vụ.
* **Infrastructure:** Docker & Docker Compose.

## Cấu trúc dự án

```text
simple_audio_bot/
│
├── docker-compose.yml       # File cấu hình Docker (Service, Volume, Network)
├── Dockerfile               # File build môi trường (Cài Playwright, FFmpeg...)
├── requirements.txt         # Danh sách thư viện Python
├── main.py                  # File chính: Điều phối luồng chạy và Lên lịch
├── README.md                # Tài liệu hướng dẫn
│
├── modules/                 # Các module chức năng
│   ├── __init__.py
│   ├── crawler.py           # Logic tìm kiếm, lấy Cookies và Tải video
│   └── audio_processor.py   # Logic cắt file âm thanh (Chunking)
│
├── data/                    # (Tự tạo) Chứa file lịch sử và cookies tạm
└── output/                  # (Tự tạo) Chứa file âm thanh thành phẩm