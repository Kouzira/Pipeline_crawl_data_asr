FROM python:3.10-slim

# Cài đặt FFmpeg, git và sqlite3 (công cụ dòng lệnh)
RUN apt-get update && \
    apt-get install -y ffmpeg git sqlite3 nodejs libsndfile1 && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .

# 1. Cài Torch CPU trước (để Docker cache layer này, không phải tải lại mỗi lần sửa code)
RUN pip install --no-cache-dir torch torchaudio --index-url https://download.pytorch.org/whl/cpu

# 2. Cài các thư viện còn lại từ requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "crawler_main.py"]