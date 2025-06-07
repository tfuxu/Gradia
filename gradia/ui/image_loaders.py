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
from typing import Optional, Callable

from gi.repository import Gtk, Gio, Gdk, GLib, Xdp
from gradia.clipboard import save_texture_to_file

ImportFormat = tuple[str, str]

class BaseImageLoader:
    """Base class for image loading handlers"""
    SUPPORTED_INPUT_FORMATS: list[ImportFormat] = [
        (".png", "image/png"),
        (".jpg", "image/jpg"),
        (".jpeg", "image/jpeg"),
        (".webp", "image/webp"),
        (".avif", "image/avif"),
    ]

    def __init__(self, window: Gtk.ApplicationWindow, temp_dir: str) -> None:
        self.window: Gtk.ApplicationWindow = window
        self.temp_dir: str = temp_dir

    def _is_supported_format(self, file_path: str) -> bool:
        """Check if file format is supported"""
        lower_path = file_path.lower()
        supported_extensions = [ext for ext, _mime in self.SUPPORTED_INPUT_FORMATS]
        return any(lower_path.endswith(ext) for ext in supported_extensions)

    def _set_image_and_update_ui(self, image_path: str, filename: str, location: str) -> None:
        """Common method to set image and update UI"""
        self.window.image_path = image_path
        if hasattr(self.window, 'drawing_overlay') and self.window.drawing_overlay:
            self.window.drawing_overlay.clear_drawing()
        self.window._update_sidebar_file_info(filename, location)
        self.window._start_processing()


class FileDialogImageLoader(BaseImageLoader):
    """Handles loading images through file dialog"""
    def __init__(self, window: Gtk.ApplicationWindow, temp_dir: str) -> None:
        super().__init__(window, temp_dir)

    def open_file_dialog(self) -> None:
        """Open file dialog to select an image"""
        file_dialog = Gtk.FileDialog()
        file_dialog.set_title(_("Open Image"))

        image_filter = Gtk.FileFilter()
        image_filter.set_name(_("Image Files"))
        for _ext, mime_type in self.SUPPORTED_INPUT_FORMATS:
            image_filter.add_mime_type(mime_type)

        filters = Gio.ListStore.new(Gtk.FileFilter)
        filters.append(image_filter)
        file_dialog.set_filters(filters)

        file_dialog.open(self.window, None, self._on_file_selected)

    def _on_file_selected(self, dialog: Gtk.FileDialog, result: Gio.AsyncResult) -> None:
        try:
            file = dialog.open_finish(result)
            if not file:
                return

            file_path = file.get_path()
            if not file_path or not os.path.isfile(file_path):
                print(f"Invalid file path: {file_path}")
                return

            if not self._is_supported_format(file_path):
                print(f"Unsupported file format: {file_path}")
                return

            filename = os.path.basename(file_path)
            directory = os.path.dirname(file_path)

            self._set_image_and_update_ui(file_path, filename, directory)

        except Exception as e:
            print(f"Error opening file: {e}")


class DragDropImageLoader(BaseImageLoader):
    def __init__(self, window: Gtk.ApplicationWindow, temp_dir: str) -> None:
        super().__init__(window, temp_dir)

    def handle_file_drop(
        self,
        drop_target: Optional[object],
        value: object,
        x: int,
        y: int
    ) -> bool:

        if not isinstance(value, Gio.File):
            return False

        file_path = value.get_path()
        if not file_path or not os.path.isfile(file_path):
            return False

        if not self._is_supported_format(file_path):
            return False

        filename = os.path.basename(file_path)
        directory = os.path.dirname(file_path)

        self._set_image_and_update_ui(file_path, filename, directory)
        return True


class ClipboardImageLoader(BaseImageLoader):
    TEMP_CLIPBOARD_FILENAME: str = "clipboard_image.png"

    def __init__(self, window: Gtk.ApplicationWindow, temp_dir: str) -> None:
        super().__init__(window, temp_dir)

    def load_from_clipboard(self) -> None:
        clipboard = self.window.get_clipboard()
        clipboard.read_texture_async(None, self._handle_clipboard_texture)

    def _handle_clipboard_texture(
        self,
        clipboard: Gdk.Clipboard,
        result: Gio.AsyncResult
    ) -> None:
        """Handle clipboard texture data"""
        try:
            texture = clipboard.read_texture_finish(result)
            if not texture:
                print("No image found in clipboard")
                self.window._show_notification(_("No image found in clipboard"))
                return

            image_path = save_texture_to_file(texture, self.temp_dir)
            if not image_path:
                raise Exception("Failed to save clipboard image to file")

            filename = _("Clipboard Image")
            location = _("From clipboard")

            self._set_image_and_update_ui(image_path, filename, location)

        except Exception as e:
            error_msg = str(e)
            if "No compatible transfer format found" in error_msg:
                self.window._show_notification(_("Clipboard does not contain an image."))
            else:
                self.window._show_notification(_("Failed to load image from clipboard."))
                print(f"Error processing clipboard image: {e}")

        finally:
            self.window._set_loading_state(False)

class ScreenshotImageLoader(BaseImageLoader):
    """Handles loading images through screenshot capture"""
    def __init__(self, window: Gtk.ApplicationWindow, temp_dir: str) -> None:
        super().__init__(window, temp_dir)
        self.portal = Xdp.Portal()
        self._error_callback: Optional[Callable[[str], None]] = None
        self._success_callback: Optional[Callable[[], None]] = None

    def take_screenshot(
        self,
        flags: Xdp.ScreenshotFlags = Xdp.ScreenshotFlags.INTERACTIVE,
        on_error_or_cancel: Optional[Callable[[str], None]] = None,
        on_success: Optional[Callable[[], None]] = None
    ) -> None:
        try:
            self._error_callback = on_error_or_cancel
            self._success_callback = on_success
            self.window.hide()
            GLib.timeout_add(150, self._do_take_screenshot, flags)
        except Exception as e:
            print(f"Failed to initiate screenshot: {e}")
            self.window._show_notification(_("Failed to take screenshot"))
            if on_error_or_cancel:
                on_error_or_cancel(str(e))

    def _do_take_screenshot(self, flags: Xdp.ScreenshotFlags) -> bool:
        try:
            self.portal.take_screenshot(
                None,
                flags,
                None,
                self._on_screenshot_taken,
                None
            )
        except Exception as e:
            print(f"Failed during screenshot: {e}")
            self.window._show_notification(_("Failed to take screenshot"))
            self.window.show()
            if self._error_callback:
                self._error_callback(str(e))
            self._error_callback = None
        return False

    def _on_screenshot_taken(self, portal_object, result, user_data) -> None:
        """Handle screenshot completion and restore window"""
        try:
            uri = self.portal.take_screenshot_finish(result)
            self._handle_screenshot_uri(uri)
        except GLib.Error as e:
            print(f"Screenshot error: {e}")
            self.window._show_notification(_("Screenshot cancelled"))
            if self._error_callback:
                self._error_callback(str(e))
        finally:
            self.window.show()
            self._error_callback = None

    def _handle_screenshot_uri(self, uri: str) -> None:
        """Process the screenshot URI and convert to local file"""
        try:
            file = Gio.File.new_for_uri(uri)
            success, contents, _unused = file.load_contents(None)
            if not success or not contents:
                raise Exception("Failed to load screenshot data")

            temp_filename = f"screenshot_{os.urandom(6).hex()}.png"
            temp_path = os.path.join(self.temp_dir, temp_filename)

            with open(temp_path, 'wb') as f:
                f.write(contents)

            filename = _("Screenshot")
            location = _("Screenshot")

            self._set_image_and_update_ui(temp_path, filename, location)
            self.window._show_notification(_("Screenshot captured!"))

            if self._success_callback:
                self._success_callback()

        except Exception as e:
            print(f"Error processing screenshot: {e}")
            self.window._show_notification(_("Failed to process screenshot"))
        finally:
            self.window._set_loading_state(False)

class CommandlineLoader(BaseImageLoader):
    """Handles loading images from command line arguments or programmatic file paths"""
    def __init__(self, window: Gtk.ApplicationWindow, temp_dir: str) -> None:
        super().__init__(window, temp_dir)

    def load_from_file(self, file_path: str) -> None:
        try:
            if not file_path:
                print("No file path provided")
                return

            if not os.path.isfile(file_path):
                print(f"File does not exist: {file_path}")
                return

            if not self._is_supported_format(file_path):
                print(f"Unsupported file format: {file_path}")
                return

            filename = os.path.basename(file_path)
            directory = os.path.dirname(file_path)

            self._set_image_and_update_ui(file_path, filename, directory)

        except Exception as e:
            print(f"Error loading file from command line: {e}")

class ImportManager:
    def __init__(self, window: Gtk.ApplicationWindow, temp_dir: str) -> None:
        self.window: Gtk.ApplicationWindow = window
        self.temp_dir: str = temp_dir

        self.file_loader: FileDialogImageLoader = FileDialogImageLoader(window, temp_dir)
        self.drag_drop_loader: DragDropImageLoader = DragDropImageLoader(window, temp_dir)
        self.clipboard_loader: ClipboardImageLoader = ClipboardImageLoader(window, temp_dir)
        self.screenshot_loader: ScreenshotImageLoader = ScreenshotImageLoader(window, temp_dir)
        self.commandline_loader: CommandlineLoader = CommandlineLoader(window, temp_dir)

    def open_file_dialog(self) -> None:
        self.file_loader.open_file_dialog()

    def _on_drop_action(self, action: Optional[object], param: object) -> None:
        if isinstance(param, GLib.Variant):
            uri = param.get_string()
            file = Gio.File.new_for_uri(uri)
            self.drag_drop_loader.handle_file_drop(None, file, 0, 0)
        else:
            print("ImportManager._on_drop_action: Invalid drop parameter")

    def load_from_clipboard(self) -> None:
        self.clipboard_loader.load_from_clipboard()

    def take_screenshot(
        self,
        flags: Xdp.ScreenshotFlags = Xdp.ScreenshotFlags.INTERACTIVE,
        on_error_or_cancel: Optional[Callable[[str], None]] = None,
        on_success: Optional[Callable[[], None]] = None
    ) -> None:
        self.screenshot_loader.take_screenshot(flags, on_error_or_cancel, on_success)

    def load_from_file(self, file_path: str) -> None:
        self.commandline_loader.load_from_file(file_path)

