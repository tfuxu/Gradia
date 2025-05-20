
import numpy as np
from PIL import Image
import math
import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Gdk, Adw

from .background import Background  # Assuming this is your base class


class GradientBackground(Background):
    def __init__(self, start_color="#4A90E2", end_color="#50E3C2", angle=0):
        self.start_color = start_color
        self.end_color = end_color
        self.angle = angle

    def prepare_image(self, width, height):
        """
        Returns a PIL Image with a linear gradient background using numpy,
        angled at self.angle degrees.
        """
        # Convert hex to RGB
        start_rgb = np.array(self._hex_to_rgb(self.start_color), dtype=np.float32)
        end_rgb = np.array(self._hex_to_rgb(self.end_color), dtype=np.float32)

        # Create coordinate grid
        x = np.linspace(0, width - 1, width)
        y = np.linspace(0, height - 1, height)
        xx, yy = np.meshgrid(x, y)

        # Convert angle to radians and compute gradient vector
        angle_rad = math.radians(self.angle % 360)
        vx = math.cos(angle_rad)
        vy = math.sin(angle_rad)

        # Project each pixel onto the gradient axis
        # Normalize pixel coords to center-based coordinates
        cx, cy = (width - 1) / 2, (height - 1) / 2
        proj = (xx - cx) * vx + (yy - cy) * vy

        # Normalize projection to [0,1]
        min_proj = proj.min()
        max_proj = proj.max()
        norm_proj = (proj - min_proj) / (max_proj - min_proj)

        # Interpolate colors
        gradient = (start_rgb[None, None, :] * (1 - norm_proj[..., None]) +
                    end_rgb[None, None, :] * norm_proj[..., None])

        # Prepare final image array with alpha channel
        img_array = np.zeros((height, width, 4), dtype=np.uint8)
        img_array[..., :3] = np.round(gradient).astype(np.uint8)
        img_array[..., 3] = 255  # Fully opaque

        return Image.fromarray(img_array, mode="RGBA")

    def _hex_to_rgb(self, hex_color):
        """Convert hex color string to RGB tuple."""
        hex_color = hex_color.lstrip('#')
        return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

    def get_name(self):
        return f"gradient-{self.start_color}-{self.end_color}-{self.angle}"


class GradientSelector:
    def __init__(self, gradient: GradientBackground, callback=None):
        self.gradient = gradient
        self.callback = callback
        self.widget = self._build_ui()

    def _build_ui(self):
        group = Adw.PreferencesGroup(title="Gradient Background")
        group.add(self._create_color_row("Start Color", self.gradient.start_color, self._on_start_color_changed))
        group.add(self._create_color_row("End Color", self.gradient.end_color, self._on_end_color_changed))
        group.add(self._create_angle_row())
        return group

    def _create_color_row(self, title, color, callback):
        row = Adw.ActionRow(title=title)
        color_button = Gtk.ColorButton()
        rgba = Gdk.RGBA()
        rgba.parse(color)
        color_button.set_rgba(rgba)
        color_button.set_valign(Gtk.Align.CENTER)
        color_button.connect("color-set", callback)
        row.add_suffix(color_button)

        if title == "Start Color":
            self.start_button = color_button
        else:
            self.end_button = color_button

        return row

    def _create_angle_row(self):
        row = Adw.ActionRow(title="Angle")
        adjustment = Gtk.Adjustment(value=self.gradient.angle, lower=0, upper=360, step_increment=45)
        self.angle_spinner = Gtk.SpinButton(adjustment=adjustment)
        self.angle_spinner.set_numeric(True)
        self.angle_spinner.set_valign(Gtk.Align.CENTER)
        self.angle_spinner.connect("value-changed", self._on_angle_changed)
        row.add_suffix(self.angle_spinner)
        return row

    def _on_start_color_changed(self, button):
        self.gradient.start_color = self._rgba_to_hex(button.get_rgba())
        self._notify_change()

    def _on_end_color_changed(self, button):
        self.gradient.end_color = self._rgba_to_hex(button.get_rgba())
        self._notify_change()

    def _on_angle_changed(self, spin_button):
        self.gradient.angle = int(spin_button.get_value())
        self._notify_change()

    def _notify_change(self):
        if self.callback:
            self.callback(self.gradient)

    def _rgba_to_hex(self, rgba):
        return "#{:02x}{:02x}{:02x}".format(
            int(rgba.red * 255),
            int(rgba.green * 255),
            int(rgba.blue * 255),
        )
