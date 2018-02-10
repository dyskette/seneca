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
import gi

gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gio, GLib

from .window import ApplicationWindow
from .dialogs import AboutDialog, InfoDialog

logger = logging.getLogger(__name__)


class Application(Gtk.Application):

    def __init__(self, extensiondir):
        """
        Initialize application class

        :param extensiondir: The path to the webkitextension directory
        """
        logger.info('Init')
        Gtk.Application.__init__(self,
                                 application_id='com.github.dyskette.Seneca',
                                 resource_base_path='/com/github/dyskette/Seneca',
                                 flags=Gio.ApplicationFlags.HANDLES_OPEN)

        self.extensiondir = extensiondir
        # self.settings = Gio.Settings.new('com.github.dyskette.Seneca')

        GLib.set_application_name('Seneca')
        GLib.set_prgname('com.github.dyskette.Seneca')
        # Set environment variable for webextension pythonloader
        GLib.setenv('PYTHONPATH', self.extensiondir, True)

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
            window.connect('delete-event', self.on_delete_event)
            window.present()

    def do_shutdown(self):
        logger.info('Shutdown')
        windows = self.get_windows()
        for window in windows:
            window.settings.save()
            window.destroy()
        Gtk.Application.do_shutdown(self)

    def do_open(self, files, n_files, hint):
        """
        Open files in current or new windows

        :param files: A list of Gio.File objects
        :param n_files: The number of files to open
        :param hint: None
        """
        if not self.get_windows():
            self.activate()

        windows = self.get_windows()
        for window in windows:
            if (not window.book.doc.path or
                window.book.doc.path == files[0].get_path()):
                window.open_file(files.pop(0))
                break
        else:
            window = ApplicationWindow(application=self)
            window.connect('delete-event', self.on_delete_event)
            window.present()
            window.open_file(files.pop(0))

    def on_delete_event(self, window, event):
        """
        Close window, save settings and quit.

        :param window: The window which called the function
        :param event: A Gdk.Event
        :return: True to stop other handlers from being invoked for the event.
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
