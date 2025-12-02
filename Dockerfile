# Dùng Image chứa sẵn Playwright và Browser (Rất nặng nhưng đầy đủ)
FROM mcr.microsoft.com/playwright/python:v1.40.0-jammy

# Vẫn phải cài FFmpeg để xử lý âm thanh
RUN apt-get update && \
    apt-get install -y ffmpeg && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

RUN playwright install chromium

COPY . .

CMD ["python", "main.py"]