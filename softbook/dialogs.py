# dialogs.py
#
# Copyright (C) 2017 Dylan Smith
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

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk

class AboutDialog():

    def __init__(self, window):
        resource = '/com/github/dyskette/softbook/ui/about.ui'
        builder = Gtk.Builder.new_from_resource(resource)

        self.about = builder.get_object('about_dialog')
        self.about.set_transient_for(window)

class FileChooserDialog(Gtk.FileChooserDialog):

    def __init__(self, title, parent):
        Gtk.FileChooserDialog.__init__(self,
                                       title,
                                       parent,
                                       (Gtk.STOCK_CANCEL,
                                        Gtk.ResponseType.CANCEL,
                                        Gtk.STOCK_OPEN,
                                        Gtk.ResponseType.ACCEPT))

class InfoDialog(Gtk.Dialog):

    def __init__(self, title, parent):
        pass

