# Copyright (C) 2025 Alexander Vanhee
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
#
# SPDX-License-Identifier: GPL-3.0-or-later

import os
import io
from PIL import Image, ImageDraw, ImageChops
import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import GdkPixbuf

from .gradient import GradientBackground
from .background import Background
from .text import Text

class ImageProcessor:
    def __init__(self, image_path=None, background=None, padding=5, aspect_ratio=None, text=None, corner_radius=2):
        self.background = background
        self.padding = padding
        self.aspect_ratio = aspect_ratio
        self.text = text
        self.corner_radius = corner_radius
        self.max_dimension = 1440
        self._max_file_size = 1000 * 1024
        self.source_img = None
        if image_path:
            self.set_image_path(image_path)

    def _get_percentage(self, value):
        return value / 100.0

    def set_image_path(self, image_path):
        if image_path != getattr(self, "_loaded_image_path", None):
            if not os.path.exists(image_path):
                raise FileNotFoundError(f"Input image not found: {image_path}")
            self.source_img = self._load_and_downscale_image(image_path)
            self._loaded_image_path = image_path

    def process(self):
        if self.source_img is None:
            raise ValueError("No image loaded to process")

        source_img = self.source_img.copy()
        width, height = source_img.size

        if self.padding < 0:
            source_img = self._crop_image(source_img)
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

    def _load_and_downscale_image(self, image_path):
        source_img = Image.open(image_path).convert("RGBA")

        if self._needs_downscaling(source_img):
            source_img = self._downscale_image(source_img)

        quality = 100
        source_img, compressed_size = self._compress_image_with_size(source_img, quality)

        while compressed_size > self._max_file_size and quality > 10:
            quality -= 10
            source_img, compressed_size = self._compress_image_with_size(source_img, quality)

        return source_img

    def _compress_image_with_size(self, image, quality):
        buffer = io.BytesIO()
        image.save(buffer, format='PNG', optimize=True, quality=quality)
        size = buffer.tell()
        buffer.seek(0)
        compressed = Image.open(buffer).convert("RGBA")
        return compressed, size

    def _needs_downscaling(self, image):
        width, height = image.size
        return width > self.max_dimension or height > self.max_dimension

    def _downscale_image(self, image):
        width, height = image.size
        if width >= height:
            new_width = self.max_dimension
            new_height = int(height * (self.max_dimension / width))
        else:
            new_height = self.max_dimension
            new_width = int(width * (self.max_dimension / height))
        return image.resize((new_width, new_height), Image.Resampling.LANCZOS)

    def _crop_image(self, image):
        width, height = image.size
        smaller_dimension = min(width, height)
        padding_percentage = self._get_percentage(abs(self.padding))
        padding_pixels = int(padding_percentage * smaller_dimension)
        crop_w = max(1, width - 2 * padding_pixels)
        crop_h = max(1, height - 2 * padding_pixels)
        offset_x = (width - crop_w) // 2
        offset_y = (height - crop_h) // 2
        return image.crop((offset_x, offset_y, offset_x + crop_w, offset_y + crop_h))

    def _calculate_final_dimensions(self, width, height):
        if self.padding >= 0:
            smaller_dimension = min(width, height)
            padding_percentage = self._get_percentage(self.padding)
            padding_pixels = int(padding_percentage * smaller_dimension)
            width += padding_pixels * 2
            height += padding_pixels * 2

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
        smaller_dimension = min(width, height)
        radius_percentage = self._get_percentage(self.corner_radius)
        radius_pixels = int(radius_percentage * smaller_dimension)

        mask = Image.new("L", (width, height), 0)
        draw = ImageDraw.Draw(mask)
        draw.rounded_rectangle((0, 0, width, height), radius=radius_pixels, fill=255)

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
