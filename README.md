# ASR Data Pipeline: High-Performance Audio Mining

Hệ thống thu thập và tiền xử lý dữ liệu âm thanh tự động quy mô lớn, được tối ưu hóa để xây dựng Dataset huấn luyện mô hình AI (Speech-to-Text / ASR) như Whisper hay Wav2Vec.

Dự án sử dụng kiến trúc **Producer-Consumer** với **Redis** làm trung gian, cho phép mở rộng (Scale) dễ dàng và quản lý cấu hình động linh hoạt.

## Tính năng nổi bật (Cập nhật mới)

* **Parallel Crawling:** Tải xuống đa luồng với `ThreadPoolExecutor`, tăng tốc độ thu thập dữ liệu gấp nhiều lần.
* **Smart Monologue Merging:**
    * Sử dụng **Silero VAD** để loại bỏ khoảng lặng.
    * Tự động gộp các câu nói ngắn gần nhau thành một đoạn **Monologue (Độc thoại)** hoàn chỉnh để giữ ngữ cảnh (Context) cho mô hình AI.
* **Cơ chế chịu lỗi (Fault Tolerance):**
    * **Safe Fail:** Task lỗi không bị mất mà được chuyển vào hàng đợi riêng để debug.
    * **Zombie Cleanup:** Tự động dọn dẹp file rác khi khởi động.
    * **Idle Detection:** Worker tự động báo cáo khi hoàn thành hết công việc.
* **Dynamic Configuration:** Cấu hình toàn bộ hệ thống (Từ khóa, Ngưỡng VAD, Số luồng...) qua file `.env` mà không cần sửa code.
* **Session Stats:** Hiển thị thống kê thời gian thực về số lượng video đã tải và số task đã xử lý.

## Công nghệ sử dụng

* **Core:** Python 3.10 (Slim), Docker & Docker Compose.
* **Broker:** Redis (Quản lý Queue).
* **Database:** SQLite (WAL Mode).
* **AI & Audio:** `torch`, `torchaudio`, `silero-vad`, `yt-dlp`.

## Cấu trúc dự án

```text
Pipeline_crawl_data_asr/
│
├── .env                 # Cấu hình hệ thống (User chỉnh sửa tại đây)
├── config.py            # Module nạp cấu hình
├── docker-compose.yml   # Orchestration
├── Dockerfile           # Environment
├── requirements.txt     # Dependencies
├── crawler_main.py      # Entrypoint Crawler
├── worker_main.py       # Entrypoint Worker
│
├── modules/             # Source code
│   ├── crawler.py       # Logic tải & đẩy task
│   ├── audio_processor.py # Logic VAD & Monologue Merge
│   └── database.py      # Logic SQLite
│
├── data/                # Dữ liệu bền vững (DB, Cookies)
└── output/              # Kết quả đầu ra (Dataset)
```

## Hướng dẫn chạy (Quick Start)

### 1. Cấu hình
Tạo file `.env` tại thư mục gốc (nếu chưa có) với nội dung mẫu:

```ini
TZ=Asia/Ho_Chi_Minh
REDIS_HOST=redis
REDIS_PORT=6379

# --- CRAWLER CONFIG ---
KEYWORDS=Tin tức VTV24,Podcast tiếng Việt,Hội thảo
MAX_WORKERS=4           # Số luồng tải song song
SEARCH_LIMIT=5          # Số video tải về cho mỗi từ khóa

# --- AUDIO & VAD CONFIG ---
SAMPLE_RATE=16000       # Chuẩn 16kHz cho Whisper
VAD_THRESHOLD=0.5       # Độ nhạy (0.5 là cân bằng)
MIN_SILENCE_MS=500      # Khoảng lặng tối thiểu (ms)

# --- MONOLOGUE MERGING ---
MONOLOGUE_MAX_PAUSE=1.5     # Gộp câu nếu nghỉ < 1.5s
MONOLOGUE_MAX_DURATION=60.0 # Độ dài tối đa 1 file (giây)
```

### 2. Khởi chạy
Dựng toàn bộ hệ thống bằng 1 lệnh duy nhất:

```bash
docker-compose up --build -d
```

### 3. Theo dõi & Giám sát

* **Xem Crawler (Tiến độ tải & Stats):**
  ```bash
  docker logs -f audio_crawler
  ```
  *Log mẫu:* `REPORT: Total videos downloaded in this session: 15`

* **Xem Worker (Tiến độ xử lý & Idle status):**
  ```bash
  docker logs -f worker
  ```
  *Log mẫu:* `[COMPLETED] Finished: Video A...` hoặc `Completed All Task!`

### 4. Cập nhật cấu hình
Khi sửa file `.env` (ví dụ đổi từ khóa), chỉ cần restart để áp dụng:

```bash
docker-compose restart crawler worker
```

## Bảo trì (Dọn dẹp ổ cứng)
Chạy lệnh sau mỗi tuần để dọn dẹp cache build và image cũ:

```bash
docker system prune -a -f

```

