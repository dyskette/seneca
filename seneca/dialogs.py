# dialogs.py
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

from . import VERSION

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk

class AboutDialog(Gtk.AboutDialog):

    def __init__(self, window):
        Gtk.AboutDialog.__init__(self,
                                 transient_for=window, modal=True,
                                 license_type=Gtk.License.GPL_3_0,
                                 authors=['Eddy Castillo', ],
                                 copyright='Copyright © 2017 Eddy Castillo',
                                 logo_icon_name='com.github.dyskette.seneca',
                                 version=VERSION)

class FileChooserDialog(Gtk.FileChooserDialog):

    def __init__(self, window):
        Gtk.FileChooserDialog.__init__(self,
                                       transient_for=window, modal=True)

        self.set_title('Open book')
        self.add_button('Open', Gtk.ResponseType.OK)
        self.add_button('Cancel', Gtk.ResponseType.CANCEL)
        self.set_default_response(Gtk.ResponseType.OK)

        filefilter = Gtk.FileFilter()
        filefilter.add_mime_type('application/epub+zip')
        self.set_filter(filefilter)

class InfoDialog(Gtk.Dialog):

    def __init__(self, title, parent):
        pass

