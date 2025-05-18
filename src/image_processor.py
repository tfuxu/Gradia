import subprocess
import os

class ImageProcessor:
    def __init__(self, start_color="#4A90E2", end_color="#50E3C2", padding=20, aspect_ratio=None):
        self.start_color = start_color
        self.end_color = end_color
        self.padding = padding
        self.aspect_ratio = aspect_ratio  # e.g., 1.777 for 16:9

    def process(self, image_path, output_path):
        try:
            identify_cmd = ["magick", "identify", "-format", "%w %h", image_path]
            result = subprocess.run(identify_cmd, capture_output=True, text=True, check=True)
            width, height = map(int, result.stdout.strip().split())
        except (subprocess.CalledProcessError, FileNotFoundError):
            try:
                identify_cmd = ["identify", "-format", "%w %h", image_path]
                result = subprocess.run(identify_cmd, capture_output=True, text=True, check=True)
                width, height = map(int, result.stdout.strip().split())
            except Exception:
                width, height = 1000, 1000

        padded_width = width + self.padding * 2
        padded_height = height + self.padding * 2

        if self.aspect_ratio:
            target_ratio = float(self.aspect_ratio)
            current_ratio = padded_width / padded_height

            if current_ratio < target_ratio:
                padded_width = int(padded_height * target_ratio)
            elif current_ratio > target_ratio:
                padded_height = int(padded_width / target_ratio)

        cmd = [
            "magick",
            "(",
            "-size", f"{padded_width}x{padded_height}",
            f"gradient:{self.start_color}-{self.end_color}",
            ")",
            "(",
            image_path,
            "-bordercolor", "none",
            "-border", str(self.padding),
            ")",
            "-gravity", "center",
            "-compose", "over",
            "-composite",
            output_path
        ]

        try:
            print("Running command:", " ".join(cmd))
            subprocess.run(cmd, check=True)
        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            print(f"Magick failed: {e}")

