import sys
import gi
import tempfile
import shutil

gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')

from gi.repository import Adw, Gtk

from .ui import GradientUI

class GradiaApp(Adw.Application):
    def __init__(self):
        super().__init__(application_id="io.github.AlexanderVanhee.Gradia")
        self.temp_dir = tempfile.mkdtemp()

    def do_activate(self):
        self.ui = GradientUI(self, self.temp_dir)
        self.ui.build_ui()
        self.ui.show()

    def do_shutdown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)
        super().do_shutdown()

def main(version=None):
    app = GradiaApp()
    app.run(sys.argv)

