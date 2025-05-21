import sys
import gi
import tempfile
import shutil

gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
gi.require_version('Gio', '2.0')

from gi.repository import Adw, Gtk, Gio, GLib
from .ui import GradientUI

class GradiaApp(Adw.Application):
    def __init__(self):
        super().__init__(
            application_id="io.github.AlexanderVanhee.Gradia",
            flags=Gio.ApplicationFlags.HANDLES_OPEN
        )
        self.temp_dir = tempfile.mkdtemp()
        self.file_to_open = None

    def do_activate(self):
        self.ui = GradientUI(self, self.temp_dir)
        self.ui.build_ui()
        self.ui.show()

    def do_open(self, files, n_files, hint):
        self.activate()

    def do_shutdown(self):
        def clean_temp():
            shutil.rmtree(self.temp_dir, ignore_errors=True)
            return False

        GLib.timeout_add(100, clean_temp)
        Adw.Application.do_shutdown(self)

def main(version=None):
    app = GradiaApp()
    app.run(sys.argv)

