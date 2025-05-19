import os
import shutil
import gi
import threading
import subprocess


gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Gtk, Gio, Adw, Gdk, GLib
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


class SolidSelector:
    def __init__(self, color="#FFFFFF", callback=None):
        self.color = color
        self.callback = callback
        self.widget = self._build_ui()

    def _build_ui(self):
        solid_group = Adw.PreferencesGroup()
        solid_group.set_title("Solid Background")

        color_row = Adw.ActionRow()
        color_row.set_title("Color")

        self.color_button = Gtk.ColorButton()
        rgba = Gdk.RGBA()
        rgba.parse(self.color)
        self.color_button.set_rgba(rgba)
        self.color_button.connect("color-set", self._on_color_set)
        self.color_button.set_valign(Gtk.Align.CENTER)
        color_row.add_suffix(self.color_button)

        solid_group.add(color_row)
        return solid_group

    def _on_color_set(self, button):
        rgba = button.get_rgba()
        self.color = "#{:02x}{:02x}{:02x}".format(
            int(rgba.red * 255),
            int(rgba.green * 255),
            int(rgba.blue * 255)
        )
        if self.callback:
            self.callback()
    def get_solid_background(self):
        return SolidBackground(color=self.color)

