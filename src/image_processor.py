import subprocess
import os
from .gradient import GradientBackground
from .background import Background

class SolidBackground(Background):
    def __init__(self, color="#FFFFFF"):
        self.color = color

    def prepare_command(self, width, height):
        return [
            "-size", f"{width}x{height}",
            f"xc:{self.color}"
        ]

    def get_name(self):
        return f"solid-{self.color}"

class ImageBackground(Background):
    def __init__(self, background_image_path, resize="fill"):
        self.background_image_path = background_image_path
        self.resize = resize  # options: none, fill, fit, stretch

    def prepare_command(self, width, height):
        resize_command = []

        if self.resize == "fill":
            resize_command = ["-resize", f"{width}x{height}^", "-gravity", "center", "-extent", f"{width}x{height}"]
        elif self.resize == "fit":
            resize_command = ["-resize", f"{width}x{height}"]
        elif self.resize == "stretch":
            resize_command = ["-resize", f"{width}x{height}!"]

        return [
            self.background_image_path,
            *resize_command
        ]

    def get_name(self):
        filename = os.path.basename(self.background_image_path)
        return f"image-{filename}-{self.resize}"


class ImageProcessor:
    def __init__(
        self,
        background=None,
        padding=20,
        aspect_ratio=None
    ):
        self.background = background or GradientBackground()
        self.padding = padding
        self.aspect_ratio = aspect_ratio

    def process(self, image_path, output_path):
        width, height = self._get_image_dimensions(image_path)

        if self.padding < 0:
            image_path, width, height = self._crop_image(image_path, output_path, width, height)

        padded_width, padded_height = self._calculate_dimensions(width, height)

        self._apply_background(image_path, output_path, padded_width, padded_height)

        self._cleanup_temp_files(image_path, output_path)

    def _get_image_dimensions(self, image_path):
        try:
            identify_cmd = ["magick", "identify", "-format", "%w %h", image_path]
            result = subprocess.run(identify_cmd, capture_output=True, text=True, check=True)
            width, height = map(int, result.stdout.strip().split())
            return width, height
        except (subprocess.CalledProcessError, FileNotFoundError):
            try:
                identify_cmd = ["identify", "-format", "%w %h", image_path]
                result = subprocess.run(identify_cmd, capture_output=True, text=True, check=True)
                width, height = map(int, result.stdout.strip().split())
                return width, height
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

    def _apply_background(self, image_path, output_path, width, height):
        try:
            cmd = ["magick"]

            # Add background creation commands
            cmd.extend(self.background.prepare_command(width, height))

            # Add foreground image with appropriate padding
            if self.padding >= 0:
                cmd.extend([
                    "(",
                    image_path,
                    "-bordercolor", "none",
                    "-border", str(self.padding),
                    ")"
                ])
            else:
                cmd.append(image_path)

            # Complete the composition
            cmd.extend([
                "-gravity", "center",
                "-compose", "over",
                "-composite",
                output_path
            ])

            subprocess.run(cmd, check=True)
        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            print(f"ImageMagick processing failed: {e}")

    def _cleanup_temp_files(self, image_path, output_path):
        if self.padding < 0 and image_path.endswith(".temp.png"):
            try:
                os.remove(image_path)
            except:
                pass
