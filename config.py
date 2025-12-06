import os
import logging
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

class Config:
    # Redis
    REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
    REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
    QUEUE_NAME = "audio_tasks"          # Queue cho Worker (Cắt)
    LABELING_QUEUE_NAME = "label_tasks" # Queue cho Labeler (Gemini) <--- MỚI
    FAILED_QUEUE_NAME = "audio_tasks_failed"

    # Paths
    BASE_DIR = "/app"
    OUTPUT_RAW = os.path.join(BASE_DIR, "output", "raw")
    OUTPUT_DATASET = os.path.join(BASE_DIR, "output", "dataset")
    OUTPUT_LABELS = os.path.join(BASE_DIR, "output", "json_labels")
    DB_PATH = os.path.join(BASE_DIR, "data", "metadata.db")
    COOKIE_FILE = os.path.join(BASE_DIR, "data", "cookies.txt")

    # Crawler
    _keywords_str = os.getenv("KEYWORDS", "Tin tức")
    KEYWORDS = [k.strip() for k in _keywords_str.split(",") if k.strip()]
    MAX_WORKERS = int(os.getenv("MAX_WORKERS", 4))
    SEARCH_LIMIT = int(os.getenv("SEARCH_LIMIT", 5))

    # Audio & VAD
    SAMPLE_RATE = int(os.getenv("SAMPLE_RATE", 16000))
    VAD_THRESHOLD = float(os.getenv("VAD_THRESHOLD", 0.5))
    MIN_SILENCE_MS = int(os.getenv("MIN_SILENCE_MS", 500))
    MIN_CHUNK_DURATION = float(os.getenv("MIN_CHUNK_DURATION", 1.0))
    
    # Monologue Merging
    MONOLOGUE_MAX_PAUSE = float(os.getenv("MONOLOGUE_MAX_PAUSE", 1.5))
    MONOLOGUE_MAX_DURATION = float(os.getenv("MONOLOGUE_MAX_DURATION", 60.0))

    # Labeling
    _keys_str = os.getenv("GEMINI_API_KEYS", "")
    GEMINI_API_KEYS = [k.strip() for k in _keys_str.split(",") if k.strip()]