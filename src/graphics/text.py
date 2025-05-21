from PIL import Image, ImageDraw, ImageFont
import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Gdk, Adw


class Text:
    """Represents text properties and provides functionality to draw text on an image."""

    VALID_GRAVITIES = [
        "northwest", "north", "northeast",
        "west", "center", "east",
        "southwest", "south", "southeast"
    ]

    def __init__(self, text, font_path=None, color="rgb(255,255,255)", size=42, gravity="south"):
        self.text = text
        self.font_path = font_path or "/usr/share/fonts/Adwaita/AdwaitaSans-Regular.ttf"
        self.color = color
        self.size = size
        self.gravity = gravity.lower() if gravity.lower() in self.VALID_GRAVITIES else "south"

    @classmethod
    def get_valid_gravities(cls):
        """Returns the list of valid gravity positions."""
        return cls.VALID_GRAVITIES.copy()

    def apply_to_image(self, img, padding=10):
        """Draw the text onto the provided PIL image with given padding."""
        if not self.text:
            return img

        draw = ImageDraw.Draw(img)
        font = self._load_font()
        fill_color = self._parse_color()
        position = self._calculate_position(draw, font, img.size, padding)

        draw.text(position, self.text, fill=fill_color, font=font)
        return img

    def _load_font(self):
        """Load the font from the font path or fall back to default."""
        try:
            return ImageFont.truetype(self.font_path, self.size)
        except Exception:
            return ImageFont.load_default()

    def _parse_color(self):
        """Parse the RGB color string into an (R, G, B) tuple."""
        if isinstance(self.color, str) and self.color.lower().startswith("rgb("):
            try:
                parts = self.color[4:-1].split(",")
                return tuple(int(p.strip()) for p in parts)
            except Exception:
                pass
        return (255, 255, 255)

    def _calculate_position(self, draw, font, image_size, padding):
        """Calculate the position where text should be drawn on the image."""
        width, height = image_size
        bbox = draw.textbbox((0, 0), self.text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        offset = padding + 25

        x = self._calculate_horizontal_position(text_width, width, offset)
        y = self._calculate_vertical_position(text_height, height, offset)

        return x, y

    def _calculate_horizontal_position(self, text_width, image_width, offset):
        if "west" in self.gravity:
            return offset
        if "east" in self.gravity:
            return image_width - text_width - offset
        # center or any other case
        return (image_width - text_width) // 2

    def _calculate_vertical_position(self, text_height, image_height, offset):
        if "north" in self.gravity:
            return offset
        if "south" in self.gravity:
            return image_height - text_height - offset
        # center or any other case
        return (image_height - text_height) // 2


class TextSelector:
    """GTK widget for selecting text properties and updating a Text object."""

    def __init__(self, text_obj: Text = None, callback=None):
        self.text_obj = text_obj or Text("")
        self.callback = callback
        self.widget, self.text_entry, self.color_button, self.size_spin, self.gravity_combo = self._build_ui()

    def _build_ui(self):
        group = Adw.PreferencesGroup(title="Text Annotation")
        self._build_text_entry(group)
        self._build_color_button(group)
        self._build_size_spin(group)
        self._build_gravity_combo(group)

        return group, self.text_entry, self.color_button, self.size_spin, self.gravity_combo

    def _build_text_entry(self, parent):
        row = Adw.ActionRow(title="Text")
        self.text_entry = Gtk.Entry(placeholder_text="Enter text")
        self.text_entry.set_text(self.text_obj.text)
        self.text_entry.set_valign(Gtk.Align.CENTER)
        self.text_entry.connect("changed", self._on_text_changed)
        row.add_suffix(self.text_entry)
        parent.add(row)

    def _build_color_button(self, parent):
        row = Adw.ActionRow(title="Color")
        self.color_button = Gtk.ColorButton()
        rgba = Gdk.RGBA()
        rgba.parse(self.text_obj.color)
        self.color_button.set_valign(Gtk.Align.CENTER)
        self.color_button.set_rgba(rgba)
        self.color_button.connect("color-set", self._on_color_changed)
        row.add_suffix(self.color_button)
        parent.add(row)

    def _build_size_spin(self, parent):
        row = Adw.ActionRow(title="Size")
        self.size_spin = Gtk.SpinButton.new_with_range(10, 100, 1)
        self.size_spin.set_valign(Gtk.Align.CENTER)
        self.size_spin.set_value(self.text_obj.size)
        self.size_spin.connect("value-changed", self._on_size_changed)
        row.add_suffix(self.size_spin)
        parent.add(row)

    def _build_gravity_combo(self, parent):
        row = Adw.ActionRow(title="Location")
        self.gravity_combo = Gtk.ComboBoxText.new()
        gravity_options = self.text_obj.get_valid_gravities()

        for gravity in gravity_options:
            self.gravity_combo.append_text(gravity)

        active_index = gravity_options.index(self.text_obj.gravity) if self.text_obj.gravity in gravity_options else gravity_options.index("south")
        self.gravity_combo.set_active(active_index)

        self.gravity_combo.set_valign(Gtk.Align.CENTER)
        self.gravity_combo.connect("changed", self._on_gravity_changed)
        row.add_suffix(self.gravity_combo)
        parent.add(row)

    def _on_text_changed(self, entry):
        self.text_obj.text = entry.get_text()
        self._notify_change()

    def _on_color_changed(self, button):
        rgba = button.get_rgba()
        self.text_obj.color = f"rgb({int(rgba.red * 255)},{int(rgba.green * 255)},{int(rgba.blue * 255)})"
        self._notify_change()

    def _on_size_changed(self, spin):
        self.text_obj.size = int(spin.get_value())
        self._notify_change()

    def _on_gravity_changed(self, combo):
        self.text_obj.gravity = combo.get_active_text()
        self._notify_change()

    def _notify_change(self):
        if self.callback:
            self.callback(self.text_obj)

