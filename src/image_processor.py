import subprocess
import os

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
        width, height = self._get_image_dimensions(image_path)

        if self.padding < 0:
            image_path, width, height = self._crop_image(image_path, output_path, width, height)

        padded_width, padded_height = self._calculate_dimensions(width, height)

        self._apply_gradient_background(image_path, output_path, padded_width, padded_height)

        self._cleanup_temp_files(image_path, output_path)

    def _get_image_dimensions(self, image_path):
        try:
            identify_cmd = ["magick", "identify", "-format", "%w %h", image_path]
            result = subprocess.run(identify_cmd, capture_output=True, text=True, check=True)
            return map(int, result.stdout.strip().split())
        except (subprocess.CalledProcessError, FileNotFoundError):
            try:
                identify_cmd = ["identify", "-format", "%w %h", image_path]
                result = subprocess.run(identify_cmd, capture_output=True, text=True, check=True)
                return map(int, result.stdout.strip().split())
            except Exception:
                return 1000, 1000

    def _crop_image(self, image_path, output_path, width, height):
        crop_width = max(1, width + 2 * self.padding)
        crop_height = max(1, height + 2 * self.padding)

        offset_x = (width - crop_width) // 2
        offset_y = (height - crop_height) // 2

        temp_image = f"{output_path}.temp.png"
        crop_cmd = [
            "magick",
            image_path,
            "-crop", f"{crop_width}x{crop_height}+{offset_x}+{offset_y}",
            temp_image
        ]

        try:
            subprocess.run(crop_cmd, check=True)
            return temp_image, crop_width, crop_height
        except (subprocess.CalledProcessError, FileNotFoundError):
            return image_path, width, height

    def _calculate_dimensions(self, width, height):
        if self.padding >= 0:
            padded_width = width + self.padding * 2
            padded_height = height + self.padding * 2
        else:
            padded_width, padded_height = width, height

        if self.aspect_ratio:
            padded_width, padded_height = self._adjust_for_aspect_ratio(padded_width, padded_height)

        return padded_width, padded_height

    def _adjust_for_aspect_ratio(self, width, height):
        target_ratio = float(self.aspect_ratio)
        current_ratio = width / height

        if current_ratio < target_ratio:
            adjusted_width = int(height * target_ratio)
            return adjusted_width, height
        elif current_ratio > target_ratio:
            adjusted_height = int(width / target_ratio)
            return width, adjusted_height

        return width, height

    def _apply_gradient_background(self, image_path, output_path, width, height):
        gradient_spec = f"gradient:{self.start_color}-{self.end_color}"

        if self.padding >= 0:
            cmd = self._build_positive_padding_command(image_path, output_path, width, height, gradient_spec)
        else:
            cmd = self._build_negative_padding_command(image_path, output_path, width, height, gradient_spec)

        try:
            subprocess.run(cmd, check=True)
        except (subprocess.CalledProcessError, FileNotFoundError):
            pass

    def _build_positive_padding_command(self, image_path, output_path, width, height, gradient_spec):
        return [
            "magick",
            "-size", f"{width}x{height}",
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

    def _build_negative_padding_command(self, image_path, output_path, width, height, gradient_spec):
        return [
            "magick",
            "-size", f"{width}x{height}",
            "-define", f"gradient:angle={self.gradient_angle}",
            gradient_spec,
            image_path,
            "-gravity", "center",
            "-compose", "over",
            "-composite",
            output_path
        ]

    def _cleanup_temp_files(self, image_path, output_path):
        if self.padding < 0 and image_path.endswith(".temp.png"):
            try:
                os.remove(image_path)
            except:
                pass

