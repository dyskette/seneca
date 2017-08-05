# book.py
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
gi.require_version('Gepub', '0.5')
from gi.repository import Gepub, WebKit2

class Book:

    def __init__(self, _gfile):
        """Initialize the book and create an Epub.Widget

        Parameters:
            _gfile (GFile): A GLib.File object

        Returns:
            None: When the initialization fails
        """
        self.fontsize_default = 16
        self.lineheight_default = 1.4
        bookpath = _gfile.get_path()

        if bookpath == '':
            raise ValueError('Book path cannot be an empty string')

        self.doc = Gepub.Doc.new(bookpath)
        self.docview = Gepub.Widget.new()
        self.docview.set_doc(self.doc)
        # Always paginate
        # TODO: Add a double page widget (too advanced for me yet)
        self.docview.set_paginate(True)

        self.__fontfamily = ''
        self.__fontweight = ''
        self.__fontstyle = ''
        self.__fontstretch = ''
        self.__fontsize = 0
        self.__lineheight = 0.0
        # TODO: Colorize book content
        self.__color = ''

        # TODO: Disable web inspector when is not needed
        webview_settings = self.docview.get_settings()
        webview_settings.set_property('enable-developer-extras', True)

    @property
    def fontfamily(self):
        return self.__fontfamily

    @fontfamily.setter
    def fontfamily(self, fontfamily):
        js_str = "document.querySelector('#gepubwrap').style.fontFamily = '%s';" % fontfamily
        self.docview.run_javascript(js_str)
        self.__fontfamily = fontfamily

    @property
    def fontstyle(self):
        return self.__fontstyle

    @fontstyle.setter
    def fontstyle(self, fontstyle):
        js_str = "document.querySelector('#gepubwrap').style.fontStyle = '%s';" % fontstyle
        self.docview.run_javascript(js_str)
        self.__fontstyle = fontstyle

    @property
    def fontstretch(self):
        return self.__fontstretch

    @fontstretch.setter
    def fontstretch(self, fontstretch):
        js_str = "document.querySelector('#gepubwrap').style.fontStretch = '%s';" % fontstretch
        self.docview.run_javascript(js_str)
        self.__fontstretch = fontstretch

    @property
    def fontweight(self):
        return self.__fontweight

    @fontweight.setter
    def fontweight(self, fontweight):
        js_str = "document.querySelector('#gepubwrap').style.fontWeight = '%s';" % fontweight
        self.docview.run_javascript(js_str)
        self.__fontweight = fontweight

    @property
    def fontsize(self):
        return self.__fontsize

    @fontsize.setter
    def fontsize(self, fontsize):
        self.docview.set_fontsize(fontsize)
        self.__fontsize = fontsize

    @property
    def lineheight(self):
        return self.__lineheight

    @lineheight.setter
    def lineheight(self, lineheight):
        self.docview.set_lineheight(lineheight)
        self.__lineheight = lineheight

    # OLD CODE
    # TODO: Theme and metadata
    # def get_metadata(self):
    #     self.title = self.document.get_metadata('title')
    #     self.author = self.document.get_metadata('creator')
    #     self.description = self.document.get_metadata('description')
    # 
    # def on_set_theme(self, button):
    #     if self.dark_theme:
    #         self.dark_theme = False
    #     else:
    #         self.dark_theme = True
    #     self.set_theme()
    #
    # def set_theme(self):
    #     #TODO: Webkit Dark theme
    #     self.settings = Gtk.Settings.get_default()
    #     if self.dark_theme:
    #         self.settings.set_property('gtk-application-prefer-dark-theme', True)
    #     else:
    #         self.settings.set_property('gtk-application-prefer-dark-theme', False)
