import os
import shutil
import gi
import threading
import subprocess
import cairo

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Gtk, Gio, Gsk, Adw, Gdk, GLib, Graphene
from .image_processor import ImageProcessor, GradientBackground, Text
from .gradient import GradientSelector
from .ui_parts import *


class GradientUI:
    def __init__(self, app, temp_dir, file=None):
        self.app = app
        self.temp_dir = temp_dir
        self.image_path = file
        self.processed_path = None
        self.current_text_object = Text(text='')
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
        self.copy_btn = None
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

        # Create save and copy button references holder
        btn_refs = [None, None]  # save_btn_ref, copy_btn_ref

        # Setup header bar
        header_bar = create_header_bar(
            save_btn_ref=btn_refs,
            on_open_clicked=self.on_open_clicked,
            on_about_clicked=self.on_about_clicked,
            on_save_clicked=self.on_save_clicked,
            on_copy_from_clicked=self.on_copy_from_clicked,
            on_copy_to_clicked=self.on_copy_to_clicked,
        )
        self.save_btn = btn_refs[0]
        self.copy_btn = btn_refs[1]
        self.toolbar_view.add_top_bar(header_bar)

        # Setup shortcuts
        setup_shortcuts(
            self.win,
            self.on_open_clicked,
            self.on_save_clicked,
            self.on_copy_from_clicked,
            self.on_copy_to_clicked,
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
            on_aspect_ratio_changed=self.on_aspect_ratio_changed,
            on_text_changed=self._on_text_changed,
            available_fonts=self.current_text_object.get_available_fonts(),
            on_font_changed=self._on_font_changed,
            text_color=self.current_text_object.color,
            on_text_color_changed=self._on_text_color_changed,
            text_size=self.current_text_object.size,
            on_text_size_changed=self._on_text_size_changed,
            text_gravity=self.current_text_object.gravity,
            on_text_gravity_changed=self._on_text_gravity_changed,
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
        self._set_save_and_copy_sensitive(True)

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



    def _on_text_changed(self, entry):
        self.current_text_object.text = entry.get_text()
        self.processor.text = self.current_text_object
        if self.image_path:
            self.process_image()

    def _on_font_changed(self, combo):
        active_iter = combo.get_active_iter()
        if active_iter is not None:
            model = combo.get_model()
            font = model[active_iter][0]
            self.current_text_object.font = font
            self.processor.text = self.current_text_object
            if self.image_path:
                self.process_image()

    def _on_text_color_changed(self, button):
        color = button.get_rgba()
        self.current_text_object.color = color.to_string()
        self.processor.text = self.current_text_object
        if self.image_path:
            self.process_image()

    def _on_text_size_changed(self, spin):
        size = int(spin.get_value())
        self.current_text_object.size = size
        self.processor.text = self.current_text_object
        if self.image_path:
            self.process_image()

    def _on_text_gravity_changed(self, combo):
        gravity = combo.get_active_text()
        if gravity:
            self.current_text_object.gravity = gravity
            self.processor.text = self.current_text_object
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
            self._set_save_and_copy_sensitive(True)
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
            self._set_save_and_copy_sensitive(True)
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

    def on_copy_from_clicked(self, button):
        self._previous_stack_child = self.image_stack.get_visible_child_name()
        self._set_loading_state(True)
        clipboard = Gdk.Display.get_default().get_clipboard()
        clipboard.read_texture_async(
            None,
            self._handle_clipboard_texture
        )

    def _set_loading_state(self, is_loading):
        if is_loading:
            self.image_stack.set_visible_child_name("loading")
            self.spinner.start()
        else:
            child = getattr(self, "_previous_stack_child", "content")
            self.image_stack.set_visible_child_name(child)
            self.spinner.stop()

    def _handle_clipboard_texture(self, clipboard, result):
        try:
            texture = clipboard.read_texture_finish(result)
            if texture is None:
                print("No image found in clipboard")
                self._set_loading_state(False)
                return

            width = texture.get_width()
            height = texture.get_height()
            print(f"dimensions: {width}:{height}")
            paintable = texture
            temp_clipboard_path = os.path.join(self.temp_dir, "clipboard_image.png")
            success = paintable.save_to_png(temp_clipboard_path)

            if not success:
                surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, width, height)
                cr = cairo.Context(surface)

                stride = surface.get_stride()
                data = bytearray(stride * height)
                texture.download(data, stride)

                mem_surface = cairo.ImageSurface.create_for_data(
                    data, cairo.FORMAT_ARGB32, width, height, stride
                )

                cr.set_source_surface(mem_surface, 0, 0)
                cr.paint()
                surface.write_to_png(temp_clipboard_path)

            self.image_path = temp_clipboard_path
            self.sidebar_info['filename_row'].set_subtitle("Clipboard Image")
            self.sidebar_info['location_row'].set_subtitle("From clipboard")
            self.sidebar.set_visible(True)
            self.process_image()
            self._set_save_and_copy_sensitive(True)

        except Exception as e:
            print(f"Error processing clipboard image: {e}")
            import traceback
            traceback.print_exc()
        finally:
            self._set_loading_state(False)

    def on_copy_to_clicked(self, button):
        if not self.processed_path or not os.path.exists(self.processed_path):
            print("No processed image to copy")
            return
        try:
            clipboard = Gdk.Display.get_default().get_clipboard()
            with open(self.processed_path, "rb") as f:
                png_data = f.read()
            content_provider = Gdk.ContentProvider.new_for_bytes("image/png", GLib.Bytes.new(png_data))
            clipboard.set_content(content_provider)

            notification = Gio.Notification.new("Image Copied")
            notification.set_body("The edited image has been copied to the clipboard.")
            self.app.send_notification("image-copied", notification)

        except Exception as e:
            print(f"Error copying processed image to clipboard: {e}")
            import traceback
            traceback.print_exc()


    def on_about_clicked(self, button):
        about = create_about_dialog()
        about.present()

    def _set_save_and_copy_sensitive(self, sensitive: bool):
        if self.save_btn:
            self.save_btn.set_sensitive(sensitive)
        if self.copy_btn:
            self.copy_btn.set_sensitive(sensitive)

