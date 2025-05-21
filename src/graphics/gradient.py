import math
import numpy as np
from PIL import Image
import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Gdk, Adw

from .background import Background

class GradientBackground(Background):
    def __init__(self, start_color="#4A90E2", end_color="#50E3C2", angle=0):
        self.start_color = start_color
        self.end_color = end_color
        self.angle = angle

    def prepare_image(self, width, height):
        start_rgb = self._to_rgb_array(self.start_color)
        end_rgb = self._to_rgb_array(self.end_color)
        xx, yy = self._meshgrid(width, height)
        proj = self._project(xx, yy, width, height)
        norm = self._normalize(proj)
        gradient = self._interpolate(start_rgb, end_rgb, norm)
        return self._to_image(gradient, width, height)

    def get_name(self):
        return f"gradient-{self.start_color}-{self.end_color}-{self.angle}"

    def _to_rgb_array(self, hex_color):
        hex_color = hex_color.lstrip("#")
        return np.array([int(hex_color[i:i + 2], 16) for i in (0, 2, 4)], dtype=np.float32)

    def _meshgrid(self, width, height):
        x = np.linspace(0, width - 1, width)
        y = np.linspace(0, height - 1, height)
        return np.meshgrid(x, y)

    def _project(self, xx, yy, width, height):
        angle_rad = math.radians(self.angle % 360)
        vx, vy = math.cos(angle_rad), math.sin(angle_rad)
        cx, cy = (width - 1) / 2, (height - 1) / 2
        return (xx - cx) * vx + (yy - cy) * vy

    def _normalize(self, projection):
        return (projection - projection.min()) / (projection.max() - projection.min())

    def _interpolate(self, start, end, norm):
        return start * (1 - norm[..., None]) + end * norm[..., None]

    def _to_image(self, gradient, width, height):
        img = np.zeros((height, width, 4), dtype=np.uint8)
        img[..., :3] = np.round(gradient).astype(np.uint8)
        img[..., 3] = 255
        return Image.fromarray(img, mode="RGBA")


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

