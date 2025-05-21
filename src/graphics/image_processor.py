import os
import io
from PIL import Image, ImageDraw, ImageFont, ImageChops
import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import GdkPixbuf

from .gradient import GradientBackground
from .background import Background
from .text import Text

class ImageProcessor:
    def __init__(self, background=None, padding=20, aspect_ratio=None, text=None, corner_radius=20):
        self.background = background
        self.padding = padding
        self.aspect_ratio = aspect_ratio
        self.text = text
        self.corner_radius = corner_radius

    def process(self, image_path):
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"Input image not found: {image_path}")

        source_img = Image.open(image_path).convert("RGBA")
        width, height = source_img.size

        if self.padding < 0:
            source_img = self._crop_image(source_img, width, height)
            width, height = source_img.size

        if self.corner_radius > 0:
            source_img = self._apply_rounded_corners(source_img)

        padded_width, padded_height = self._calculate_final_dimensions(width, height)
        final_img = self._create_background(padded_width, padded_height)
        paste_position = self._get_paste_position(width, height, padded_width, padded_height)
        final_img.paste(source_img, paste_position, source_img)

        if self.text:
            final_img = self.text.apply_to_image(final_img)

        return self._pil_to_pixbuf(final_img)

    def _crop_image(self, image, width, height):
        crop_w = max(1, width + 2 * self.padding)
        crop_h = max(1, height + 2 * self.padding)
        offset_x = (width - crop_w) // 2
        offset_y = (height - crop_h) // 2
        return image.crop((offset_x, offset_y, offset_x + crop_w, offset_y + crop_h))

    def _calculate_final_dimensions(self, width, height):
        if self.padding >= 0:
            width += self.padding * 2
            height += self.padding * 2

        if self.aspect_ratio:
            width, height = self._adjust_for_aspect_ratio(width, height)

        return width, height

    def _adjust_for_aspect_ratio(self, width, height):
        try:
            ratio = self._parse_aspect_ratio()
            current = width / height

            if current < ratio:
                width = int(height * ratio)
            elif current > ratio:
                height = int(width / ratio)

            return width, height
        except:
            return width, height

    def _parse_aspect_ratio(self):
        if isinstance(self.aspect_ratio, str) and ":" in self.aspect_ratio:
            w, h = map(float, self.aspect_ratio.split(":"))
            return w / h
        return float(self.aspect_ratio)

    def _apply_rounded_corners(self, image):
        width, height = image.size
        mask = Image.new("L", (width, height), 0)
        draw = ImageDraw.Draw(mask)
        draw.rounded_rectangle((0, 0, width, height), radius=self.corner_radius, fill=255)

        r, g, b, alpha = image.split()
        new_alpha = ImageChops.multiply(alpha, mask)
        return Image.merge("RGBA", (r, g, b, new_alpha))

    def _create_background(self, width, height):
        if self.background:
            return self.background.prepare_image(width, height)
        return Image.new("RGBA", (width, height), (0, 0, 0, 0))

    def _get_paste_position(self, img_w, img_h, bg_w, bg_h):
        if self.padding >= 0:
            x = (bg_w - img_w) // 2
            y = (bg_h - img_h) // 2
            return x, y
        return 0, 0

    def _pil_to_pixbuf(self, image):
        if image.mode == 'RGBA':
            background = Image.new('RGB', image.size, (255, 255, 255))
            background.paste(image, mask=image.split()[3])
            image = background

        if image.mode != 'RGB':
            image = image.convert('RGB')

        buffer = io.BytesIO()
        image.save(buffer, format='PNG')
        buffer.seek(0)

        loader = GdkPixbuf.PixbufLoader.new_with_type('png')
        loader.write(buffer.read())
        loader.close()

        return loader.get_pixbuf()

