import os
import shutil
import gi
import threading
import subprocess


gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Gtk, Gio, Adw, Gdk, GLib
from .background import Background


class GradientBackground(Background):
    def __init__(self, start_color="#4A90E2", end_color="#50E3C2", angle=0):
        self.start_color = start_color
        self.end_color = end_color
        self.angle = angle

    def prepare_command(self, width, height):
        gradient_spec = f"gradient:{self.start_color}-{self.end_color}"
        return [
            "-size", f"{width}x{height}",
            "-define", f"gradient:angle={self.angle}",
            gradient_spec
        ]

    def get_name(self):
        return f"gradient-{self.start_color}-{self.end_color}-{self.angle}"


class GradientSelector:
    def __init__(self, start_color="#4A90E2", end_color="#50E3C2", angle=0, callback=None):
        self.start_color = start_color
        self.end_color = end_color
        self.angle = angle
        self.callback = callback
        self.widget = self._build_ui()

    def _build_ui(self):
        gradient_group = Adw.PreferencesGroup()
        gradient_group.set_title("Gradient Background")

        # Start Color
        start_row = Adw.ActionRow()
        start_row.set_title("Start Color")

        self.start_button = Gtk.ColorButton()
        start_rgba = Gdk.RGBA()
        start_rgba.parse(self.start_color)
        self.start_button.set_rgba(start_rgba)
        self.start_button.connect("color-set", self._on_start_color_set)
        self.start_button.set_valign(Gtk.Align.CENTER)
        start_row.add_suffix(self.start_button)
        gradient_group.add(start_row)

        # End Color
        end_row = Adw.ActionRow()
        end_row.set_title("End Color")

        self.end_button = Gtk.ColorButton()
        end_rgba = Gdk.RGBA()
        end_rgba.parse(self.end_color)
        self.end_button.set_rgba(end_rgba)
        self.end_button.connect("color-set", self._on_end_color_set)
        self.end_button.set_valign(Gtk.Align.CENTER)
        end_row.add_suffix(self.end_button)
        gradient_group.add(end_row)

        # Angle
        angle_row = Adw.ActionRow()
        angle_row.set_title("Angle")

        angle_adjustment = Gtk.Adjustment(value=self.angle, lower=0, upper=360, step_increment=45, page_increment=45)
        self.angle_spinner = Gtk.SpinButton()
        self.angle_spinner.set_adjustment(angle_adjustment)
        self.angle_spinner.set_numeric(True)
        self.angle_spinner.set_valign(Gtk.Align.CENTER)
        self.angle_spinner.connect("value-changed", self._on_angle_changed)

        angle_row.add_suffix(self.angle_spinner)
        gradient_group.add(angle_row)

        return gradient_group

    def _on_start_color_set(self, button):
        rgba = button.get_rgba()
        self.start_color = "#{:02x}{:02x}{:02x}".format(
            int(rgba.red * 255),
            int(rgba.green * 255),
            int(rgba.blue * 255)
        )
        if self.callback:
            self.callback()

    def _on_end_color_set(self, button):
        rgba = button.get_rgba()
        self.end_color = "#{:02x}{:02x}{:02x}".format(
            int(rgba.red * 255),
            int(rgba.green * 255),
            int(rgba.blue * 255)
        )
        if self.callback:
            self.callback()

    def _on_angle_changed(self, spin_button):
        self.angle = int(spin_button.get_value())
        if self.callback:
            self.callback()

    def get_gradient_background(self):
        return GradientBackground(
            start_color=self.start_color,
            end_color=self.end_color,
            angle=self.angle
        )

