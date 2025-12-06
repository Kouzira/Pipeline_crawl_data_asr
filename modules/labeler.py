import google.generativeai as genai
import os
import json
import time
import logging
import random
from pathlib import Path
from datetime import datetime
from config import Config
from google.generativeai.types import HarmCategory, HarmBlockThreshold

logger = logging.getLogger("AutoLabeler")

class GeminiLabeler:
    def __init__(self):
        if not Config.GEMINI_API_KEYS:
            logger.warning("No GEMINI_API_KEYS found!")
            self.api_ready = False
        else:
            self.api_ready = True
            self.output_dir = Config.OUTPUT_LABELS
            os.makedirs(self.output_dir, exist_ok=True)
            
            self.safety_settings = {
                HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
            }

    def _get_random_model(self):
        api_key = random.choice(Config.GEMINI_API_KEYS)
        genai.configure(api_key=api_key)
        return genai.GenerativeModel('gemini-2.5-flash')

    # --- SỬA HÀM NÀY: Xử lý 1 file thay vì cả folder ---
    def process_single_file(self, video_id, file_path, filename):
        """Xử lý 1 file audio duy nhất"""
        if not self.api_ready: return False

        # Kiểm tra nếu file JSON đã tồn tại thì bỏ qua (tránh làm lại)
        json_path = os.path.join(self.output_dir, video_id, filename.replace('.wav', '.json'))
        if os.path.exists(json_path):
            logger.info(f"Skipped (Exist): {filename}")
            return True

        # Transcribe
        transcript = self._transcribe_single(file_path)
        
        if transcript:
            self._save_json(video_id, filename, transcript)
            logger.info(f"Label Done: {filename}")
            return True
        else:
            logger.warning(f"Label Failed: {filename}")
            return False

    def _transcribe_single(self, audio_path, retry=3):
        # ... (Giữ nguyên logic cũ, không đổi) ...
        for attempt in range(retry):
            try:
                model = self._get_random_model()
                myfile = genai.upload_file(audio_path)
                
                prompt = """
                Transcribe exactly what is said in Vietnamese. 
                Lowercase. No punctuation. 
                If background noise/music only, return "[NO_SPEECH]".
                """
                
                result = model.generate_content(
                    [prompt, myfile], 
                    safety_settings=self.safety_settings
                )
                
                text = ""
                try:
                    text = result.text.strip()
                except ValueError:
                    if result.prompt_feedback and result.prompt_feedback.block_reason:
                        text = "[BLOCKED_BY_SAFETY]"
                    else:
                        text = "[EMPTY_RESPONSE]"

                try: genai.delete_file(myfile.name)
                except: pass
                
                return text

            except Exception as e:
                err = str(e)
                if "429" in err or "quota" in err.lower(): 
                    logger.warning(f"Rate limit hit, retrying...")
                    time.sleep(2) 
                else:
                    logger.error(f"Error transcribing {os.path.basename(audio_path)}: {e}")
                    return None
        return None

    def _save_json(self, video_id, filename, transcript):
        # ... (Giữ nguyên logic cũ) ...
        data = {
            "video_id": video_id,
            "filename": filename,
            "transcript": transcript,
            "timestamp": datetime.now().isoformat(),
            "model": "gemini-2.5-flash"
        }
        
        save_path = os.path.join(self.output_dir, video_id)
        os.makedirs(save_path, exist_ok=True)
        
        json_name = filename.replace('.wav', '.json')
        full_path = os.path.join(save_path, json_name)
        
        with open(full_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)