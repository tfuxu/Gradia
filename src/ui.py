import os
import shutil
import gi
import threading

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Gtk, Gio, Adw, Gdk, GLib
from .image_processor import ImageProcessor

class GradientUI:
    def __init__(self, app, temp_dir, file=None):
        self.app = app
        self.temp_dir = temp_dir
        self.image_path = file
        self.processed_path = None
        # Default image processor config
        self.processor = ImageProcessor()
        # Initialize parameters from processor defaults
        self.start_color = self.processor.start_color
        self.end_color = self.processor.end_color
        self.angle = self.processor.gradient_angle
        self.padding = self.processor.padding

        self.win = None
        self.save_btn = None

    # --- UI Building ---

    def build_ui(self):
        self.win = Adw.ApplicationWindow(application=self.app)
        self.win.set_title("Gradia")
        self.win.set_default_size(900, 600)

        shortcut_controller = Gtk.ShortcutController()

        open_shortcut = Gtk.Shortcut.new(
            Gtk.ShortcutTrigger.parse_string("<Ctrl>O"),
            Gtk.CallbackAction.new(lambda *args: self.on_open_clicked(None))
        )

        save_shortcut = Gtk.Shortcut.new(
            Gtk.ShortcutTrigger.parse_string("<Ctrl>S"),
            Gtk.CallbackAction.new(
                lambda *args: self.on_save_clicked(None) if self.save_btn and self.save_btn.get_sensitive() else None
            )
        )

        shortcut_controller.add_shortcut(open_shortcut)
        shortcut_controller.add_shortcut(save_shortcut)
        self.win.add_controller(shortcut_controller)

        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)

        # Header bar with open and save buttons
        header_bar = Adw.HeaderBar()

        open_icon = Gtk.Image.new_from_icon_name("document-open-symbolic")
        open_btn = Gtk.Button()
        open_btn.set_child(open_icon)
        open_btn.get_style_context().add_class("flat")
        open_btn.set_tooltip_text("Open Image")
        open_btn.connect("clicked", self.on_open_clicked)
        header_bar.pack_start(open_btn)

        about_icon = Gtk.Image.new_from_icon_name("help-about-symbolic")
        about_btn = Gtk.Button()
        about_btn.get_style_context().add_class("flat")
        about_btn.set_child(about_icon)
        about_btn.set_tooltip_text("About Gradia")
        about_btn.connect("clicked", self.on_about_clicked)
        header_bar.pack_end(about_btn)

        save_btn = Gtk.Button.new_with_label("Save Image")
        save_btn.get_style_context().add_class("suggested-action")
        save_btn.connect("clicked", self.on_save_clicked)
        self.save_btn = save_btn
        self.save_btn.set_sensitive(False)
        header_bar.pack_end(save_btn)

        main_box.append(header_bar)

        # Main horizontal paned area (image / sidebar)
        self.main_paned = Gtk.Paned(orientation=Gtk.Orientation.HORIZONTAL)
        self.main_paned.set_position(650)
        self.main_paned.set_vexpand(True)

        # Image stack: image preview, loading spinner, or empty status
        self.image_stack = Gtk.Stack()
        self.image_stack.get_style_context().add_class("view")
        self.image_stack.set_vexpand(True)
        self.image_stack.set_hexpand(True)

        self.picture = Gtk.Picture()
        self.picture.set_content_fit(Gtk.ContentFit.CONTAIN)
        self.picture.set_can_shrink(True)
        self.image_stack.add_named(self.picture, "image")

        spinner_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        spinner_box.set_valign(Gtk.Align.CENTER)
        spinner_box.set_halign(Gtk.Align.CENTER)
        spinner_box.set_spacing(0)
        spinner_box.set_margin_top(20)
        spinner_box.set_margin_bottom(20)
        spinner_box.set_margin_start(20)
        spinner_box.set_margin_end(20)

        self.spinner = Gtk.Spinner()
        self.spinner.set_vexpand(False)
        self.spinner.set_hexpand(False)

        spinner_box.append(self.spinner)
        self.image_stack.add_named(spinner_box, "loading")

        # Add drop targets for drag & drop of image files
        drop_target = Gtk.DropTarget.new(Gio.File, Gdk.DragAction.COPY)
        drop_target.set_preload(True)
        drop_target.connect("drop", self.on_file_dropped)
        self.image_stack.add_controller(drop_target)

        # Status page for no image loaded
        status_page = Adw.StatusPage()
        status_page.set_icon_name("image-x-generic-symbolic")
        status_page.set_title("No Image Loaded")

        open_status_btn = Gtk.Button(label="Open Image")
        open_status_btn.set_halign(Gtk.Align.CENTER)
        open_status_btn.get_style_context().add_class("suggested-action")
        open_status_btn.get_style_context().add_class("pill")
        open_status_btn.get_style_context().add_class("text-button")
        open_status_btn.connect("clicked", self.on_open_clicked)
        status_page.set_child(open_status_btn)

        self.image_stack.add_named(status_page, "empty")
        self.image_stack.set_visible_child_name("empty")
        self.main_paned.set_start_child(self.image_stack)

        # Sidebar for settings (initially hidden)
        self.sidebar = self.create_sidebar_ui()
        self.sidebar.set_size_request(250, -1)
        self.sidebar.set_visible(False)
        self.main_paned.set_end_child(self.sidebar)

        main_box.append(self.main_paned)

        self.win.set_content(main_box)

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
        self.filename_row.set_subtitle(filename)
        self.location_row.set_subtitle(directory)
        self.sidebar.set_visible(True)

        self.image_stack.set_visible_child_name("loading")
        self.spinner.start()

        self.process_image()
        self.save_btn.set_sensitive(True)

    def create_sidebar_ui(self):
        sidebar_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)

        settings_scroll = Gtk.ScrolledWindow()
        settings_scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        settings_scroll.set_vexpand(True)

        controls_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=20)
        controls_box.set_margin_start(16)
        controls_box.set_margin_end(16)
        controls_box.set_margin_top(16)
        controls_box.set_margin_bottom(16)

        # Gradient Colors Group
        gradient_group = Adw.PreferencesGroup()
        gradient_group.set_title("Gradient Background")

        # Start Color
        start_row = Adw.ActionRow()
        start_row.set_title("Start Color")

        self.start_button = Gtk.ColorButton()
        start_rgba = Gdk.RGBA()
        start_rgba.parse(self.start_color)
        self.start_button.set_rgba(start_rgba)
        self.start_button.connect("color-set", self.on_start_color_set)
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
        self.end_button.connect("color-set", self.on_end_color_set)
        self.end_button.set_valign(Gtk.Align.CENTER)
        end_row.add_suffix(self.end_button)
        gradient_group.add(end_row)

        angle_row = Adw.ActionRow()
        angle_row.set_title("Angle")

        angle_adjustment = Gtk.Adjustment(value=self.angle, lower=0, upper=360, step_increment=45, page_increment=45)
        self.angle_spinner = Gtk.SpinButton()
        self.angle_spinner.set_adjustment(angle_adjustment)
        self.angle_spinner.set_numeric(True)
        self.angle_spinner.set_valign(Gtk.Align.CENTER)
        self.angle_spinner.connect("value-changed", self.on_angle_changed)

        angle_row.add_suffix(self.angle_spinner)
        gradient_group.add(angle_row)

        controls_box.append(gradient_group)

        # Image Options Group
        padding_group = Adw.PreferencesGroup()
        padding_group.set_title("Image Options")

        padding_row = Adw.ActionRow()
        padding_row.set_title("Padding")

        padding_adjustment = Gtk.Adjustment(value=self.padding, lower=0, upper=500, step_increment=10, page_increment=50)
        self.padding_spinner = Gtk.SpinButton()
        self.padding_spinner.set_adjustment(padding_adjustment)
        self.padding_spinner.set_numeric(True)
        self.padding_spinner.connect("value-changed", self.on_padding_changed)
        self.padding_spinner.set_valign(Gtk.Align.CENTER)
        padding_row.add_suffix(self.padding_spinner)
        padding_group.add(padding_row)

        aspect_ratio_row = Adw.ActionRow()
        aspect_ratio_row.set_title("Aspect Ratio")

        self.aspect_ratio_entry = Gtk.Entry()
        self.aspect_ratio_entry.set_placeholder_text("16:9")
        self.aspect_ratio_entry.set_valign(Gtk.Align.CENTER)
        self.aspect_ratio_entry.connect("changed", self.on_aspect_ratio_changed)

        aspect_ratio_row.add_suffix(self.aspect_ratio_entry)
        padding_group.add(aspect_ratio_row)

        controls_box.append(padding_group)

        # File Info Group
        file_info_group = Adw.PreferencesGroup()
        file_info_group.set_title("Current File")

        self.filename_row = Adw.ActionRow()
        self.filename_row.set_title("Name")
        self.filename_row.set_subtitle("No file loaded")
        file_info_group.add(self.filename_row)

        self.location_row = Adw.ActionRow()
        self.location_row.set_title("Location")
        self.location_row.set_subtitle("No file loaded")
        file_info_group.add(self.location_row)

        controls_box.append(file_info_group)

        settings_scroll.set_child(controls_box)
        sidebar_box.append(settings_scroll)

        return sidebar_box

    # --- Event Handlers ---

    def on_start_color_set(self, button):
        rgba = button.get_rgba()
        self.start_color = "#{:02x}{:02x}{:02x}".format(
            int(rgba.red * 255),
            int(rgba.green * 255),
            int(rgba.blue * 255)
        )
        self.processor.start_color = self.start_color
        if self.image_path:
            self.process_image()

    def on_end_color_set(self, button):
        rgba = button.get_rgba()
        self.end_color = "#{:02x}{:02x}{:02x}".format(
            int(rgba.red * 255),
            int(rgba.green * 255),
            int(rgba.blue * 255)
        )
        self.processor.end_color = self.end_color
        if self.image_path:
            self.process_image()
    def on_angle_changed(self, spin_button):
        self.angle = int(spin_button.get_value())
        self.processor.gradient_angle = self.angle
        if self.image_path:
            self.process_image()

    def on_padding_changed(self, spin_button):
        self.padding = int(spin_button.get_value())
        self.processor.padding = self.padding
        if self.image_path:
            self.process_image()

    def on_aspect_ratio_changed(self, entry):
        text = entry.get_text().strip()

        if not text:
            self.processor.aspect_ratio = None
            if self.image_path:
                self.process_image()
            return

        try:
            if ":" in text:
                num, denom = map(float, text.split(":"))
                ratio = num / denom
            else:
                ratio = float(text)

            if ratio <= 0:
                raise ValueError("Aspect ratio must be positive")

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
            self.filename_row.set_subtitle(filename)
            self.location_row.set_subtitle(directory)
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

        self.processor.start_color = self.start_color
        self.processor.end_color = self.end_color
        self.processor.padding = self.padding

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
            self.spinner.stop()
            self.image_stack.set_visible_child_name("image")
        return False

    def on_save_clicked(self, button):
        if not self.processed_path or not os.path.exists(self.processed_path):
            return

        save_dialog = Gtk.FileDialog()
        save_dialog.set_title("Save Modified Image")

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
            self.filename_row.set_subtitle(filename)
            self.location_row.set_subtitle(directory)
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
        about = Adw.AboutWindow(transient_for=self.win, modal=True)
        about.set_application_name("Gradia")
        about.set_version("0.1")
        about.set_comments("Make your images ready for the world")
        about.set_website("")
        about.set_developer_name("Alexander Vanhee")
        about.present()


