# 🎙️ ASR Data Pipeline: High-Performance Audio Mining

Hệ thống thu thập và tiền xử lý dữ liệu âm thanh tự động quy mô lớn phục vụ huấn luyện mô hình AI (Speech-to-Text / ASR). 

Dự án sử dụng kiến trúc **Producer-Consumer** với **Redis** làm trung gian, cho phép mở rộng (Scale) số lượng Worker xử lý song song, tối ưu hóa tốc độ và tài nguyên.

## Tính năng nổi bật

* **Parallel Crawling (Đa luồng):** Crawler sử dụng `ThreadPoolExecutor` để tìm kiếm và tải xuống nhiều video cùng lúc, tăng tốc độ thu thập gấp nhiều lần.
* **Smart Segmentation (VAD):** Không cắt cứng theo thời gian (30s). Sử dụng model AI **Silero VAD** (Voice Activity Detection) để cắt chính xác các đoạn có giọng nói, loại bỏ khoảng lặng và nhạc nền.
* **RAM Optimized:** Sử dụng `torchaudio` thay thế `pydub`, xử lý Tensor trực tiếp giúp giảm 50% lượng RAM tiêu thụ, ngăn chặn lỗi tràn bộ nhớ (OOM).
* **Scalable Architecture:** Dễ dàng tăng số lượng Worker (x2, x5, x10) chỉ bằng một lệnh Docker, tận dụng tối đa sức mạnh CPU đa nhân.
* **Anti-Ban Strategy:** Tích hợp cơ chế giả lập User-Agent, Random Sleep và sử dụng Cookies Netscape để tránh bị YouTube chặn (HTTP 429).
* **Standardized Output:** Dữ liệu đầu ra được chuẩn hóa tự động: **WAV, 16kHz, Mono Channel** (Chuẩn vàng cho model Whisper, Wav2Vec).

## 🛠️ Công nghệ sử dụng

* **Core Logic:** Python 3.10 (Slim Image)
* **Message Broker:** Redis (Quản lý hàng đợi Task)
* **Database:** SQLite (Lưu metadata, tránh trùng lặp video)
* **Libraries:**
    * `yt-dlp`: Tải video/audio hiệu năng cao.
    * `torch` & `torchaudio`: Xử lý tín hiệu âm thanh.
    * `silero-vad`: Model phát hiện giọng nói.
    * `schedule`: Lên lịch chạy định kỳ.

## Cấu trúc dự án

```text
Pipeline_crawl_data_asr/
│
├── docker-compose.yml       # Điều phối Redis, Crawler và Worker
├── Dockerfile               # Môi trường chạy (cài sẵn FFmpeg, Libsndfile)
├── requirements.txt         # Các thư viện phụ thuộc
├── crawler_main.py          # Entrypoint cho Crawler
├── worker_main.py           # Entrypoint cho Worker
│
├── modules/                 # Source code chính
│   ├── crawler.py           # Logic tải đa luồng & đẩy task vào Redis
│   ├── audio_processor.py   # Logic cắt file dùng Silero VAD & Torchaudio
│   └── database.py          # Quản lý SQLite
│
├── data/                    # Thư mục dữ liệu bền vững (Persistence)
│   ├── metadata.db          # Database (Tự tạo khi chạy)
│   ├── cookies.txt          # File cookies (Bạn cần tự thêm vào)
│   └── torch_cache/         # Cache model VAD (tránh tải lại mỗi lần)
│
└── output/                  # Dữ liệu đầu ra
    ├── raw/                 # Audio gốc (Tự xóa sau khi xử lý xong)
    └── dataset/             # Thành phẩm: Folder chứa các đoạn audio đã cắt