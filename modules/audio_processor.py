import torch
import torchaudio
import os
import gc
import logging
from config import Config

logger = logging.getLogger("VAD_Processor")

class VADSplitter:
    def __init__(self, output_dir=Config.OUTPUT_DATASET):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
        
        logger.info("Loading Silero VAD model...")
        self.model, utils = torch.hub.load(repo_or_dir='snakers4/silero-vad',
                                           model='silero_vad',
                                           force_reload=False,
                                           onnx=False)
        (self.get_speech_timestamps, _, self.read_audio, _, _) = utils

    def _merge_timestamps(self, timestamps, sample_rate):
        """
        Gộp các đoạn speech ngắn lại thành monologue nếu khoảng nghỉ giữa chúng nhỏ.
        """
        if not timestamps:
            return []

        merged = []
        # Chuyển đổi giây sang số mẫu (samples) để so sánh chính xác
        max_pause_samples = int(Config.MONOLOGUE_MAX_PAUSE * sample_rate)
        max_duration_samples = int(Config.MONOLOGUE_MAX_DURATION * sample_rate)

        # Lấy đoạn đầu tiên làm mốc
        current_segment = timestamps[0]

        for next_segment in timestamps[1:]:
            pause_duration = next_segment['start'] - current_segment['end']
            total_duration = next_segment['end'] - current_segment['start']

            # Logic Gộp:
            # 1. Khoảng nghỉ (pause) nhỏ hơn mức cho phép
            # 2. Tổng độ dài sau khi gộp chưa vượt quá giới hạn
            if (pause_duration < max_pause_samples) and (total_duration < max_duration_samples):
                # Kéo dài đoạn hiện tại ra đến cuối đoạn tiếp theo
                current_segment['end'] = next_segment['end']
            else:
                # Nếu không gộp được thì lưu đoạn cũ lại và bắt đầu đoạn mới
                merged.append(current_segment)
                current_segment = next_segment

        # Đừng quên lưu đoạn cuối cùng
        merged.append(current_segment)
        return merged

    def process_file(self, file_path, video_id):
        if not os.path.exists(file_path): 
            logger.warning(f"File not found: {file_path}")
            return []
        
        wav = None
        try:
            # 1. Load Audio
            wav = self.read_audio(file_path, sampling_rate=Config.SAMPLE_RATE)
            
            # 2. Get Timestamps (Các đoạn nhỏ lẻ)
            speech_timestamps = self.get_speech_timestamps(
                wav, self.model, 
                sampling_rate=Config.SAMPLE_RATE, 
                threshold=Config.VAD_THRESHOLD, 
                min_silence_duration_ms=Config.MIN_SILENCE_MS
            )
            
            if not speech_timestamps: 
                logger.info(f"No speech detected for {video_id}")
                return []

            # 3. --- MONOLOGUE MERGE (BƯỚC MỚI) ---
            # Gộp các đoạn nhỏ thành đoạn lớn
            merged_timestamps = self._merge_timestamps(speech_timestamps, Config.SAMPLE_RATE)
            logger.info(f"[{video_id}] Merged {len(speech_timestamps)} raw chunks -> {len(merged_timestamps)} monologues.")

            save_folder = os.path.join(self.output_dir, video_id)
            os.makedirs(save_folder, exist_ok=True)
            
            chunks_info = []
            
            for i, ts in enumerate(merged_timestamps):
                start_sample = int(ts['start'])
                end_sample = int(ts['end'])
                
                duration = (end_sample - start_sample) / Config.SAMPLE_RATE
                
                if duration >= Config.MIN_CHUNK_DURATION:
                    filename = f"{video_id}_{i:04d}.wav"
                    out_path = os.path.join(save_folder, filename)
                    
                    # Cắt đoạn wav
                    chunk = wav[start_sample:end_sample]
                    
                    # Thêm chiều channel [1, samples]
                    chunk = chunk.unsqueeze(0)
                    
                    torchaudio.save(out_path, chunk, Config.SAMPLE_RATE)
                    
                    chunks_info.append({'path': out_path, 'duration': float(duration)})

            return chunks_info

        except Exception as e:
            logger.error(f"Error processing {video_id}: {e}", exc_info=True)
            return []
        
        finally:
            if wav is not None:
                del wav
            gc.collect()