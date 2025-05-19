import os
import shutil
import gi
import threading
import subprocess

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Gtk, Gio, Adw, Gdk, GLib
from .image_processor import ImageProcessor, GradientBackground
from .gradient import GradientSelector
from .ui_parts import *


class GradientUI:
    def __init__(self, app, temp_dir, file=None):
        self.app = app
        self.temp_dir = temp_dir
        self.image_path = file
        self.processed_path = None
        self.processor = ImageProcessor()

        # Initialize core properties
        self.padding = self.processor.padding
        initial_start_color = "#4A90E2"
        initial_end_color = "#50E3C2"
        initial_angle = 0

        # Initialize gradient selector with callback
        self.gradient_selector = GradientSelector(
            start_color=initial_start_color,
            end_color=initial_end_color,
            angle=initial_angle,
            callback=self._on_gradient_changed
        )

        # UI elements (populated during build_ui)
        self.win = None
        self.save_btn = None
        self.picture = None
        self.spinner = None
        self.image_stack = None
        self.toolbar_view = None
        self.sidebar = None
        self.sidebar_info = None
        self.main_paned = None

    def build_ui(self):
        # Create window
        self.win = Adw.ApplicationWindow(application=self.app)
        self.win.set_title("Gradia")
        self.win.set_default_size(900, 600)

        # Create toolbar view
        self.toolbar_view = Adw.ToolbarView()
        self.toolbar_view.set_top_bar_style(Adw.ToolbarStyle.FLAT)
        self.win.set_content(self.toolbar_view)

        # Create save button reference holder
        save_btn_ref = [None]

        # Setup header bar
        header_bar = create_header_bar(
            save_btn_ref=save_btn_ref,
            on_open_clicked=self.on_open_clicked,
            on_about_clicked=self.on_about_clicked,
            on_save_clicked=self.on_save_clicked
        )
        self.save_btn = save_btn_ref[0]
        self.toolbar_view.add_top_bar(header_bar)

        # Setup shortcuts
        setup_shortcuts(
            self.win,
            self.on_open_clicked,
            self.on_save_clicked,
            self.save_btn
        )

        # Setup image stack
        stack_info = create_image_stack(
            self.on_file_dropped,
            self.on_open_clicked
        )
        self.image_stack = stack_info[0]
        self.picture = stack_info[1]
        self.spinner = stack_info[2]

        # Create sidebar
        self.sidebar_info = create_sidebar_ui(
            gradient_selector_widget=self.gradient_selector.widget,
            padding=self.padding,
            on_padding_changed=self.on_padding_changed,
            on_aspect_ratio_changed=self.on_aspect_ratio_changed
        )
        self.sidebar = self.sidebar_info['sidebar']
        self.sidebar.set_size_request(250, -1)
        self.sidebar.set_visible(False)

        # Create main paned container
        self.main_paned = Gtk.Paned(orientation=Gtk.Orientation.HORIZONTAL)
        self.main_paned.set_position(650)
        self.main_paned.set_vexpand(True)
        self.main_paned.set_start_child(self.image_stack)
        self.main_paned.set_end_child(self.sidebar)
        self.toolbar_view.set_content(self.main_paned)

    def show(self):
        self.win.present()

        if self.image_path:
            self._load_initial_file()

    def _load_initial_file(self):
        if not os.path.isfile(self.image_path):
            print(f"Initial file path does not exist: {self.image_path}")
            return

        filename = os.path.basename(self.image_path)
        directory = os.path.dirname(self.image_path)
        self.sidebar_info['filename_row'].set_subtitle(filename)
        self.sidebar_info['location_row'].set_subtitle(directory)
        self.sidebar.set_visible(True)

        self.image_stack.set_visible_child_name("loading")
        self.spinner.start()

        self.process_image()
        self.save_btn.set_sensitive(True)

    def _on_gradient_changed(self):
        """Called when any gradient setting is changed"""
        self.processor.background = self.gradient_selector.get_gradient_background()
        if self.image_path:
            self.process_image()

    def on_padding_changed(self, spin_button):
        self.padding = int(spin_button.get_value())
        self.processor.padding = self.padding
        if self.image_path:
            self.process_image()

    @staticmethod
    def parse_aspect_ratio(text: str) -> float | None:
        text = text.strip()
        if not text:
            return None
        if ":" in text:
            num, denom = map(float, text.split(":"))
            if denom == 0:
                raise ValueError("Denominator cannot be zero")
            return num / denom
        return float(text)

    @staticmethod
    def check_aspect_ratio_bounds(ratio: float, min_ratio=0.2, max_ratio=5) -> bool:
        return min_ratio <= ratio <= max_ratio

    def on_aspect_ratio_changed(self, entry):
        text = entry.get_text().strip()
        try:
            ratio = self.parse_aspect_ratio(text)
            if ratio is None:
                self.processor.aspect_ratio = None
                if self.image_path:
                    self.process_image()
                return
            if not self.check_aspect_ratio_bounds(ratio):
                raise ValueError(f"Aspect ratio must be between 0.2 and 5 (got {ratio})")
            self.processor.aspect_ratio = ratio
            if self.image_path:
                self.process_image()

        except Exception as e:
            print(f"Invalid aspect ratio: {text} ({e})")

    def on_open_clicked(self, button):
        file_dialog = Gtk.FileDialog()
        file_dialog.set_title("Open Image")

        image_filter = Gtk.FileFilter()
        image_filter.set_name("Image Files")
        image_filter.add_mime_type("image/png")
        image_filter.add_mime_type("image/jpeg")
        image_filter.add_mime_type("image/jpg")

        filters = Gio.ListStore.new(Gtk.FileFilter)
        filters.append(image_filter)
        file_dialog.set_filters(filters)

        file_dialog.open(self.win, None, self._on_file_selected)

    def _on_file_selected(self, dialog, result):
        try:
            file = dialog.open_finish(result)
            self.image_path = file.get_path()
            filename = os.path.basename(self.image_path)
            directory = os.path.dirname(self.image_path)
            self.sidebar_info['filename_row'].set_subtitle(filename)
            self.sidebar_info['location_row'].set_subtitle(directory)
            self.sidebar.set_visible(True)

            # Show spinner while processing
            self.image_stack.set_visible_child_name("loading")
            self.spinner.start()

            self.process_image()
            self.save_btn.set_sensitive(True)
        except Exception as e:
            print(f"Error opening file: {e}")

    def process_image(self):
        if not self.image_path:
            return

        if self.processed_path and os.path.exists(self.processed_path):
            try:
                os.remove(self.processed_path)
            except Exception:
                pass

        self.processed_path = os.path.join(self.temp_dir, "processed.png")

        # Run processing in background
        threading.Thread(target=self._process_in_background, daemon=True).start()

    def _process_in_background(self):
        try:
            self.processor.process(self.image_path, self.processed_path)
            # Schedule UI update on the main thread
            GLib.idle_add(self._update_image_preview, priority=GLib.PRIORITY_DEFAULT)
        except Exception as e:
            print(f"Error processing image: {e}")

    def _update_image_preview(self):
        if os.path.exists(self.processed_path):
            self.picture.set_file(Gio.File.new_for_path(self.processed_path))
            try:
                identify_cmd = ["magick", "identify", "-format", "%wx%h", self.processed_path]
                result = subprocess.run(identify_cmd, capture_output=True, text=True, check=True)
                size_str = result.stdout.strip()
                self.sidebar_info['processed_size_row'].set_subtitle(size_str)
            except Exception as e:
                self.sidebar_info['processed_size_row'].set_subtitle("Error")
                print(f"Error getting processed image size: {e}")

            self.spinner.stop()
            self.image_stack.set_visible_child_name("image")

            self.image_stack.get_style_context().add_class("view")
            self.toolbar_view.set_top_bar_style(Adw.ToolbarStyle.RAISED)
        return False

    def on_save_clicked(self, button):
        if not self.processed_path or not os.path.exists(self.processed_path):
            return

        save_dialog = Gtk.FileDialog()
        save_dialog.set_title("Save Edited Image")

        if self.image_path:
            original_name = os.path.splitext(os.path.basename(self.image_path))[0]
            dynamic_name = f"{original_name}_processed.png"
        else:
            dynamic_name = "processed.png"

        save_dialog.set_initial_name(dynamic_name)

        png_filter = Gtk.FileFilter()
        png_filter.set_name("PNG Image")
        png_filter.add_mime_type("image/png")
        filters = Gio.ListStore.new(Gtk.FileFilter)
        filters.append(png_filter)
        save_dialog.set_filters(filters)
        save_dialog.save(self.win, None, self._on_save_finished)

    def on_file_dropped(self, drop_target, value, x, y):
        if not isinstance(value, Gio.File):
            return False

        path = value.get_path()
        if path and os.path.isfile(path) and path.lower().endswith((".png", ".jpg", ".jpeg")):
            self.image_path = path
            filename = os.path.basename(path)
            directory = os.path.dirname(path)
            self.sidebar_info['filename_row'].set_subtitle(filename)
            self.sidebar_info['location_row'].set_subtitle(directory)
            self.sidebar.set_visible(True)

            # Show spinner while processing
            self.image_stack.set_visible_child_name("loading")
            self.spinner.start()

            self.process_image()
            self.save_btn.set_sensitive(True)
            return True

        return False

    def _on_save_finished(self, dialog, result):
        try:
            file = dialog.save_finish(result)
            if file is None:
                return

            save_path = file.get_path()
            shutil.copy(self.processed_path, save_path)
        except Exception as e:
            print(f"Error saving file: {e}")

    def on_about_clicked(self, button):
        about = create_about_dialog()
        about.present()
