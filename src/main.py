import sys
import gi
import tempfile
import shutil

gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
gi.require_version('Gio', '2.0')

from gi.repository import Adw, Gtk, Gio, GLib
from .window import GradientWindow

class GradiaApp(Adw.Application):
    def __init__(self, version=None):
        super().__init__(
            application_id="be.alexandervanhee.gradia",
            flags=Gio.ApplicationFlags.HANDLES_OPEN
        )
        self.temp_dir = tempfile.mkdtemp()
        self.version = version
        self.file_to_open = None

    def do_activate(self):
        self.ui = GradientWindow(self, self.temp_dir, version=self.version)
        self.ui.build_ui()
        self.ui.show()

    def do_open(self, files, n_files, hint):
        self.activate()

    def do_shutdown(self):
        shutil.rmtree(self.temp_dir)
        Adw.Application.do_shutdown(self)

def main(version=None):
    try:
        app = GradiaApp(version=version)
        return app.run(sys.argv)
    except Exception as e:
        print('Application closed with an exception:', e)
        return 1

