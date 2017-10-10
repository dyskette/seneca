# application.py
#
# Copyright (C) 2017 Eddy Castillo
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
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import os
import logging
logger = logging.getLogger(__name__)

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gio, GLib

from .window import ApplicationWindow
from .dialogs import AboutDialog, InfoDialog

class Application(Gtk.Application):

    def __init__(self, extensiondir):
        logger.info('Init')
        Gtk.Application.__init__(self,
                                 application_id='com.github.dyskette.Seneca',
                                 resource_base_path='/com/github/dyskette/Seneca',
                                 flags=Gio.ApplicationFlags.HANDLES_OPEN)

        GLib.set_application_name('Seneca')
        GLib.set_prgname('com.github.dyskette.Seneca')

        # Set environment variable for webextension pythonloader
        self.extensiondir = extensiondir
        GLib.setenv('PYTHONPATH', self.extensiondir, True)
        # self.settings = Gio.Settings.new('com.github.dyskette.Seneca')

    def do_startup(self):
        logger.info('Startup')
        Gtk.Application.do_startup(self)

        action = Gio.SimpleAction.new('about')
        action.connect('activate', self.on_about)
        self.add_action(action)

        action = Gio.SimpleAction.new('quit')
        action.connect('activate', self.on_quit)
        self.add_action(action)

    def do_activate(self):
        logger.info('Activate')
        if not self.get_windows():
            window = ApplicationWindow(application=self)
            window.present()

    def do_shutdown(self):
        logger.info('Shutdown')
        windows = self.get_windows()
        for window in windows:
            window.settings.save()
            window.destroy()
        Gtk.Application.do_shutdown(self)

    def do_open(self, files, n_files, hint):
        logger.info('Open')
        if not self.get_windows():
            w = ApplicationWindow(application=self)
            w.connect('delete-event', self.on_delete_event)

        windows = self.get_windows()

        for giofile in files:
            for window in windows:
                if window.book.get_path() == giofile.get_path():
                    window.open_file(giofile)
                    window.present()
                    break
            else:
                for window in windows:
                    if window.book.get_doc() is None:
                        window.open_file(giofile)
                        window.present()
                        break
                else:
                    window = ApplicationWindow(application=self)
                    window.connect('delete-event', self.on_delete_event)
                    window.open_file(giofile)
                    window.present()

    def on_delete_event(self, window, event):
        """Close window, save settings and quit.

        Args:
            window (Gtk.Window)
            event (Gdk.Event)

        Returns:
            True to stop other handlers from being invoked for the event.
        """
        if len(self.get_windows()) > 1:
            window.settings.save()
            window.destroy()
        else:
            self.quit()

        return True

    def on_about(self, action, param):
        dialog = AboutDialog(self.get_active_window())
        dialog.present()

    def on_quit(self, action, param):
        self.quit()
