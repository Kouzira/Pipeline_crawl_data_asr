from pydub import AudioSegment # pyright: ignore[reportMissingImports]
import math
import os

class AudioSplitter:
    def __init__(self, output_dir="/app/output/dataset"):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)

    def split_fixed_length(self, file_path, duration_sec=30):
        if not os.path.exists(file_path): return []

        print(f"Đang cắt file: {os.path.basename(file_path)}")
        try:
            audio = AudioSegment.from_file(file_path)
        except Exception:
            return []

        chunk_length_ms = duration_sec * 1000
        total_chunks = math.ceil(len(audio) / chunk_length_ms)
        
        video_name = os.path.splitext(os.path.basename(file_path))[0]
        save_path = os.path.join(self.output_dir, video_name)
        os.makedirs(save_path, exist_ok=True)

        for i, start_ms in enumerate(range(0, len(audio), chunk_length_ms)):
            chunk = audio[start_ms : start_ms + chunk_length_ms]
            output_file = os.path.join(save_path, f"part_{i:03d}.wav")
            chunk.export(output_file, format="wav")

        print(f"Xong! Đã lưu {total_chunks} file tại: {save_path}")
        return True