import subprocess
import tempfile
import os
import gi
from PIL import Image
import hashlib

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Gdk, Adw

from .background import Background

class GradientBackground:
    _gradient_cache = {}
    _max_cache_size = 100

    def __init__(self, start_color="#4A90E2", end_color="#50E3C2", angle=0):
        self.start_color = start_color
        self.end_color = end_color
        self.angle = angle

    def get_name(self):
        return f"gradient-{self.start_color}-{self.end_color}-{self.angle}"

    def prepare_image(self, width, height):
        cache_key = (self.start_color, self.end_color, self.angle, width, height)
        if cache_key in self._gradient_cache:
            return self._gradient_cache[cache_key].copy()

        if len(self._gradient_cache) >= self._max_cache_size:
            keys_to_remove = list(self._gradient_cache.keys())[:self._max_cache_size // 2]
            for key in keys_to_remove:
                del self._gradient_cache[key]

        # Create temporary file for output
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp_output:
            output_path = tmp_output.name

        try:
            gradient_spec = f"gradient:{self.start_color}-{self.end_color}"
            size_arg = f"{width}x{height}"

            # Use gradient direction without rotating image
            cmd = [
                "magick",
                "-size", size_arg,
                f"-define", f"gradient:angle={self.angle}",
                gradient_spec,
                output_path
            ]

            # Execute command
            subprocess.run(cmd, check=True)

            # Load the result into a PIL image
            image = Image.open(output_path).convert("RGBA")

            # Cache and return
            self._gradient_cache[cache_key] = image.copy()
            return image

        finally:
            if os.path.exists(output_path):
                os.remove(output_path)
    @classmethod
    def clear_cache(cls):
        """Clear the gradient cache manually if needed"""
        cls._gradient_cache.clear()

    @classmethod
    def get_cache_info(cls):
        """Get information about the current cache state"""
        return {
            'cache_size': len(cls._gradient_cache),
            'max_cache_size': cls._max_cache_size,
            'cached_gradients': list(cls._gradient_cache.keys())
        }


class GradientSelector:
    def __init__(self, gradient: GradientBackground, callback=None):
        self.gradient = gradient
        self.callback = callback
        self.widget = self._build()

    def _build(self):
        group = Adw.PreferencesGroup(title="Gradient Background")
        group.add(self._color_row("Start Color", self.gradient.start_color, self._on_start))
        group.add(self._color_row("End Color", self.gradient.end_color, self._on_end))
        group.add(self._angle_row())
        return group

    def _color_row(self, label, value, handler):
        row = Adw.ActionRow(title=label)
        button = self._color_button(value, handler)
        row.add_suffix(button)
        return row

    def _color_button(self, hex_color, handler):
        rgba = self._hex_to_rgba(hex_color)
        button = Gtk.ColorButton()
        button.set_rgba(rgba)
        button.set_valign(Gtk.Align.CENTER)
        button.connect("color-set", handler)
        return button

    def _angle_row(self):
        row = Adw.ActionRow(title="Angle")
        spin = self._angle_spinner()
        row.add_suffix(spin)
        return row

    def _angle_spinner(self):
        adj = Gtk.Adjustment(value=self.gradient.angle, lower=0, upper=360, step_increment=45)
        spin = Gtk.SpinButton(adjustment=adj)
        spin.set_numeric(True)
        spin.set_valign(Gtk.Align.CENTER)
        spin.connect("value-changed", self._on_angle)
        return spin

    def _on_start(self, button):
        self.gradient.start_color = self._rgba_to_hex(button.get_rgba())
        self._notify()

    def _on_end(self, button):
        self.gradient.end_color = self._rgba_to_hex(button.get_rgba())
        self._notify()

    def _on_angle(self, spin):
        self.gradient.angle = int(spin.get_value())
        self._notify()

    def _notify(self):
        if self.callback:
            self.callback(self.gradient)

    def _hex_to_rgba(self, hex_color):
        rgba = Gdk.RGBA()
        rgba.parse(hex_color)
        return rgba

    def _rgba_to_hex(self, rgba):
        r = int(rgba.red * 255)
        g = int(rgba.green * 255)
        b = int(rgba.blue * 255)
        return f"#{r:02x}{g:02x}{b:02x}"


