import os
from PIL import Image, ImageDraw, ImageFont, ImageChops
import io
import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Gdk, GLib, GdkPixbuf

from .gradient import GradientBackground
from .background import Background

from PIL import ImageFont, ImageDraw

class Text:
    def __init__(self, text, font_path=None, color="rgb(255,255,255)", size=42, gravity="south"):
        self.text = text
        self.font_path = font_path or "/usr/share/fonts/Adwaita/AdwaitaSans-Regular.ttf"
        self.color = color
        self.size = size
        self.gravity = gravity.lower()

    def apply_to_image(self, img, padding=10):
        if not self.text:
            return img

        margin = 25
        total_padding = padding + margin

        width, height = img.size
        draw = ImageDraw.Draw(img)

        try:
            font = ImageFont.truetype(self.font_path, self.size)
        except Exception as e:
            print(f"Failed to load font '{self.font_path}': {e}")
            font = ImageFont.load_default()
            print("Loaded default font instead.")

        text_bbox = draw.textbbox((0, 0), self.text, font=font)
        text_width = text_bbox[2] - text_bbox[0]
        text_height = text_bbox[3] - text_bbox[1]

        if "west" in self.gravity:
            x = total_padding
        elif "east" in self.gravity:
            x = width - text_width - total_padding
        else:
            x = (width - text_width) // 2

        if "north" in self.gravity:
            y = total_padding
        elif "south" in self.gravity:
            y = height - text_height - total_padding
        else:
            y = (height - text_height) // 2

        if isinstance(self.color, str):
            c = self.color.lower().strip()
            if c.startswith("rgb(") and c.endswith(")"):
                try:
                    parts = c[4:-1].split(",")
                    color = tuple(int(p.strip()) for p in parts)
                    if len(color) != 3:
                        raise ValueError("RGB color must have exactly 3 components")
                except Exception as e:
                    print(f"Invalid rgb color format '{self.color}': {e}. Defaulting to white.")
                    color = (255, 255, 255)
            else:
                print(f"Unsupported color format '{self.color}'. Only 'rgb(r,g,b)' supported. Defaulting to white.")
                color = (255, 255, 255)
        else:
            color = self.color

        draw.text((x, y), self.text, fill=color, font=font)

        return img


class ImageProcessor:
    def __init__(
        self,
        background=None,
        padding=20,
        aspect_ratio=None,
        text=None,
        corner_radius=20
    ):
        self.background = background
        self.padding = padding
        self.aspect_ratio = aspect_ratio
        self.text = text
        self.corner_radius = corner_radius

    def process(self, image_path):
        """
        Process the image and return a GdkPixbuf.Pixbuf suitable for GTK4.

        Args:
            image_path: Path to the input image file

        Returns:
            GdkPixbuf.Pixbuf: A GTK4-compatible image buffer
        """
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"Input image not found: {image_path}")

        source_img = Image.open(image_path).convert("RGBA")
        width, height = source_img.size

        # Handle negative padding (cropping)
        if self.padding < 0:
            crop_width = max(1, width + 2 * self.padding)
            crop_height = max(1, height + 2 * self.padding)
            offset_x = (width - crop_width) // 2
            offset_y = (height - crop_height) // 2
            source_img = source_img.crop((
                offset_x,
                offset_y,
                offset_x + crop_width,
                offset_y + crop_height
            ))
            width, height = source_img.size

        # Apply rounded corners if needed
        if self.corner_radius > 0:
            source_img = self._apply_rounded_corners(source_img, self.corner_radius)

        # Calculate final dimensions
        padded_width, padded_height = self._calculate_dimensions(width, height)

        # Create background
        if self.background:
            final_img = self.background.prepare_image(padded_width, padded_height)
        else:
            final_img = Image.new("RGBA", (padded_width, padded_height), (0, 0, 0, 0))

        # Center image with padding
        if self.padding >= 0:
            paste_x = (padded_width - width) // 2
            paste_y = (padded_height - height) // 2
        else:
            paste_x = paste_y = 0

        final_img.paste(source_img, (paste_x, paste_y), source_img)

        # Apply text if provided
        if self.text:
            final_img = self.text.apply_to_image(final_img)

        return self._pil_to_pixbuf(final_img)

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
        try:
            if isinstance(self.aspect_ratio, str) and ":" in self.aspect_ratio:
                w, h = map(float, self.aspect_ratio.split(":"))
                target_ratio = w / h
            else:
                target_ratio = float(self.aspect_ratio)

            current_ratio = width / height

            if current_ratio < target_ratio:
                adjusted_width = int(height * target_ratio)
                return adjusted_width, height
            elif current_ratio > target_ratio:
                adjusted_height = int(width / target_ratio)
                return width, adjusted_height

            return width, height
        except Exception as e:
            print(f"Warning: Error adjusting aspect ratio: {e}")
            return width, height

    def _apply_rounded_corners(self, image, radius):
        """Apply rounded corners to the image preserving existing semi-transparency."""
        width, height = image.size
        mask = Image.new("L", (width, height), 0)
        draw = ImageDraw.Draw(mask)
        draw.rounded_rectangle((0, 0, width, height), radius=radius, fill=255)

        # Split image into RGBA channels
        r, g, b, alpha = image.split()

        # Multiply original alpha by mask (pixel-wise)
        new_alpha = Image.eval(alpha, lambda a: a)  # Copy alpha
        new_alpha = ImageChops.multiply(alpha, mask)

        # Combine back with original RGB channels
        rounded = Image.merge("RGBA", (r, g, b, new_alpha))

        return rounded

    def _pil_to_pixbuf(self, pil_image):
        if pil_image.mode == 'RGBA':
            background = Image.new('RGB', pil_image.size, (255, 255, 255))
            background.paste(pil_image, mask=pil_image.split()[3])
            pil_image = background

        if pil_image.mode != 'RGB':
            pil_image = pil_image.convert('RGB')

        buffer = io.BytesIO()
        pil_image.save(buffer, format='PNG')
        buffer.seek(0)

        loader = GdkPixbuf.PixbufLoader.new_with_type('png')
        loader.write(buffer.read())
        loader.close()

        return loader.get_pixbuf()
