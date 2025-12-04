import torch
import torchaudio
import os
import gc

class VADSplitter:
    def __init__(self, output_dir):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
        print("[VAD] Loading Silero VAD...")
        self.model, utils = torch.hub.load(repo_or_dir='snakers4/silero-vad',
                                           model='silero_vad',
                                           force_reload=False,
                                           onnx=False)
        (self.get_speech_timestamps, _, self.read_audio, _, _) = utils

    def process_file(self, file_path, video_id, min_sec=5.0, max_sec=20.0):
        if not os.path.exists(file_path): return []
        
        try:
            # 1. Load Audio
            # Silero trả về Tensor 1 chiều: [samples]
            wav = self.read_audio(file_path, sampling_rate=16000)
            
            # 2. Get Timestamps
            speech_timestamps = self.get_speech_timestamps(
                wav, self.model, sampling_rate=16000, threshold=0.5, min_silence_duration_ms=500
            )
            
            if not speech_timestamps: return []

            save_folder = os.path.join(self.output_dir, video_id)
            os.makedirs(save_folder, exist_ok=True)
            
            chunks_info = []
            
            for i, ts in enumerate(speech_timestamps):
                # Convert sample index to seconds
                start_sample = int(ts['start'])
                end_sample = int(ts['end'])
                
                duration = (end_sample - start_sample) / 16000
                
                if duration >= 1.0: # Chỉ lấy đoạn > 1s
                    filename = f"{video_id}_{i:04d}.wav"
                    out_path = os.path.join(save_folder, filename)
                    
                    # --- ĐÃ SỬA LỖI TẠI ĐÂY ---
                    # 1. Cắt trên 1 chiều (đúng bản chất dữ liệu)
                    chunk = wav[start_sample:end_sample]
                    
                    # 2. Thêm lại chiều channel (unsqueeze) để torchaudio chịu lưu (thành [1, samples])
                    chunk = chunk.unsqueeze(0)
                    
                    torchaudio.save(out_path, chunk, 16000)
                    
                    chunks_info.append({'path': out_path, 'duration': float(duration)})

            # Dọn dẹp RAM
            del wav
            gc.collect()
            
            return chunks_info

        except Exception as e:
            # In thêm traceback để dễ debug nếu có lỗi khác
            import traceback
            traceback.print_exc()
            print(f"[VAD Error] {e}")
            return []