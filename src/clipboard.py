import os

from gi.repository import Gdk, GLib

def save_texture_to_file(texture, temp_dir):
    width = texture.get_width()
    height = texture.get_height()
    temp_path = os.path.join(temp_dir, "clipboard_image.png")
    texture.save_to_png(temp_path)
    return temp_path

def save_pixbuff_to_path(temp_dir, pixbuff):
    TEMP_FILE_NAME = "clipboard_temp.png"
    temp_path = os.path.join(temp_dir, TEMP_FILE_NAME)

    pixbuff.savev(temp_path, "png", [], [])
    return temp_path

def copy_file_to_clipboard(local_path):
    with open(local_path, "rb") as f:
        png_data = f.read()

    bytes_data = GLib.Bytes.new(png_data)
    clipboard = Gdk.Display.get_default().get_clipboard()
    content_provider = Gdk.ContentProvider.new_for_bytes("image/png", bytes_data)
    clipboard.set_content(content_provider)

