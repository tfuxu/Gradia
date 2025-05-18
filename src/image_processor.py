import subprocess

class ImageProcessor:
    def __init__(
        self,
        start_color="#4A90E2",
        end_color="#50E3C2",
        padding=20,
        aspect_ratio=None,
        gradient_angle=0
    ):
        self.start_color = start_color
        self.end_color = end_color
        self.padding = padding
        self.aspect_ratio = aspect_ratio
        self.gradient_angle = gradient_angle

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

        gradient_spec = f"gradient:{self.start_color}-{self.end_color}"

        cmd = [
            "magick",
            "-size", f"{padded_width}x{padded_height}",
            "-define", f"gradient:angle={self.gradient_angle}",
            gradient_spec,
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
            subprocess.run(cmd, check=True)
        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            print(f"ImageMagick processing failed: {e}")

