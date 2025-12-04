from pydub import AudioSegment
import os

class AudioSplitter:
    def __init__(self, output_dir="/app/output/dataset"):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)

    def split_smart_30s(self, file_path, target_sec=30, max_extension_sec=10, silence_thresh=-40):
        if not os.path.exists(file_path): return []

        print(f"[SMART CUT] Đang xử lý: {os.path.basename(file_path)}")
        try:
            audio = AudioSegment.from_file(file_path)
        except Exception as e:
            print(f"❌ Lỗi đọc audio: {e}")
            return []

        target_ms = target_sec * 1000
        max_extension_ms = max_extension_sec * 1000
        total_len_ms = len(audio)
        
        start = 0
        exported_files = []
        
        video_name = os.path.splitext(os.path.basename(file_path))[0]
        save_path = os.path.join(self.output_dir, video_name)
        os.makedirs(save_path, exist_ok=True)

        chunk_index = 0

        while start < total_len_ms:
            end = start + target_ms
            if end >= total_len_ms:
                self._export_chunk(audio[start:], save_path, chunk_index)
                break

            actual_end = end
            found_silence = False
            search_limit = min(end + max_extension_ms, total_len_ms)
            
            # Tìm khoảng lặng để cắt
            for check_point in range(end, search_limit, 100):
                sample = audio[check_point : check_point + 200]
                if sample.dBFS < silence_thresh:
                    actual_end = check_point + 100
                    found_silence = True
                    break
            
            if not found_silence:
                actual_end = search_limit

            self._export_chunk(audio[start:actual_end], save_path, chunk_index)
            exported_files.append(f"{save_path}/part_{chunk_index:04d}.wav")
            
            start = actual_end
            chunk_index += 1

        print(f"Đã cắt thành {len(exported_files)} file.")
        return exported_files

    def _export_chunk(self, chunk, folder, index):
        if len(chunk) < 1000: return
        filename = f"part_{index:04d}.wav"
        chunk.export(os.path.join(folder, filename), format="wav")