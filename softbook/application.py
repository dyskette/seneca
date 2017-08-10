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
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gio, GLib

from .window import ApplicationWindow
from .dialogs import AboutDialog, InfoDialog
from .book import Book

class Application(Gtk.Application):

    def __init__(self):
        Gtk.Application.__init__(self,
                                 application_id='com.github.dyskette.softbook',
                                 flags=Gio.ApplicationFlags.HANDLES_OPEN)

        GLib.set_application_name('Softbook')
        GLib.set_prgname('softbook')

        self.window = None
        # self.settings = Gio.Settings.new('com.github.dyskette.softbook')

    def do_startup(self):
        Gtk.Application.do_startup(self)

        action = Gio.SimpleAction.new('about')
        action.connect('activate', self.on_about)
        self.add_action(action)

        action = Gio.SimpleAction.new('quit')
        action.connect('activate', self.on_quit)
        self.add_action(action)

    def do_activate(self):
        if not self.window:
            self.window = ApplicationWindow(application=self)

        self.window.present()

    def do_shutdown(self):
        Gtk.Application.do_shutdown(self)

    def do_open(self, files, n_files, hint):
        print('Number of files:', n_files)
        print('But we open just one file.')
        if not self.window:
            self.window = ApplicationWindow(application=self)

        self.window.open_file(files[0])
        # And continue...
        self.activate()

    def on_about(self, action, param):
        dialog = AboutDialog(self.get_active_window())
        dialog.about.present()

    def on_quit(self, action, param):
        self.quit()
