# window.py
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

from .gi_composites import GtkTemplate
from .book import Book
from .font import pangoFont, cssFont

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gio, GLib

@GtkTemplate(ui='/com/github/dyskette/softbook/ui/window.ui')
class ApplicationWindow(Gtk.ApplicationWindow):
    __gtype_name__ = 'ApplicationWindow'

    header_bar = GtkTemplate.Child()
    open_menu = GtkTemplate.Child()
    main_popover = GtkTemplate.Child()
    main_view = GtkTemplate.Child()
    prev_btn = GtkTemplate.Child()
    next_btn = GtkTemplate.Child()
    font_btn = GtkTemplate.Child()
    font_less = GtkTemplate.Child()
    font_default = GtkTemplate.Child()
    font_more = GtkTemplate.Child()
    font_label = GtkTemplate.Child()
    lineheight_less = GtkTemplate.Child()
    lineheight_default = GtkTemplate.Child()
    lineheight_more = GtkTemplate.Child()
    lineheight_label = GtkTemplate.Child()

    def __init__(self, application):
        Gtk.ApplicationWindow.__init__(self, application=application)
        self.init_template()
        self.book = None
        self.settings = {}

        variant = GLib.Variant.new_string('black')
        action = Gio.SimpleAction.new_stateful('color', variant.get_type(), variant)
        action.connect('change-state', self.change_color)
        self.add_action(action)

        # Initialize with headerbar buttons disabled
        self.prev_btn.set_sensitive(False)
        self.next_btn.set_sensitive(False)
        self.open_menu.set_sensitive(False)

    def open_file(self, _gfile):
        try:
            self.book = Book(_gfile)
            # TODO: Settings probably should be in book.py
            # TODO: Connect settings to page load (fami, weig, styl, stre,)
            # FIXME: Settings only last current page. See previous TODO
            # self.settings = Settings.load()
            self.settings = {'font-family': 'Roboto Condensed',
                             'font-weight': '400',
                             'font-style': 'normal',
                             'font-stretch': 'condensed',
                             'font-size':  17,
                             'font-lineheight': 1.8,
                             'color': 'light'}
            self.change_font(self.settings['font-family'],
                             self.settings['font-weight'],
                             self.settings['font-style'],
                             self.settings['font-stretch'],
                             self.settings['font-size'])
            self.change_lineheight(self.settings['font-lineheight'])

            # Add to view and show it
            self.main_view.pack_end(self.book.docview, True, True, 0)
            self.book.docview.show_all()
            # Make headerbar buttons available
            self.prev_btn.set_sensitive(True)
            self.next_btn.set_sensitive(True)
            self.open_menu.set_sensitive(True)
            # Sync buttons with settings
            pango_font = pangoFont(self.settings['font-family'],
                                   self.settings['font-weight'],
                                   self.settings['font-style'],
                                   self.settings['font-stretch'],
                                   self.settings['font-size'])
            self.font_btn.set_font_desc(pango_font.desc)
            self.font_label.set_label('{0}px'.format(self.book.fontsize))
            self.lineheight_label.set_label('{0}pt'.format(self.book.lineheight))
        except Exception as e:
            print(e)
            #TODO: Use an application notification.

    def change_fontsize(self, fontsize):
        self.book.fontsize = fontsize
        self.font_less.set_sensitive(fontsize > 8)
        self.font_more.set_sensitive(fontsize < 32)
        self.font_label.set_label('{0}px'.format(self.book.fontsize))

    def change_font(self, fontfamily, fontweight, fontstyle, fontstretch, fontsize):
        self.book.fontfamily = fontfamily
        self.book.fontweight = fontweight
        self.book.fontstyle = fontstyle
        self.book.fontstretch = fontstretch
        self.change_fontsize(fontsize)

    def change_lineheight(self, lineheight):
        self.book.lineheight = float(format(lineheight, '1.2f'))
        self.lineheight_less.set_sensitive(lineheight > 1.0)
        self.lineheight_more.set_sensitive(lineheight < 2.4)
        self.lineheight_label.set_label('{0}pt'.format(self.book.lineheight))

    def change_color(self, action, value):
        print(value.get_string())
        action.set_state(value)
        # self.book.color = _color
        # if _color == 'white':

    @GtkTemplate.Callback
    def on_font_set(self, widget):
        pango_fontdesc = widget.get_property('font-desc')
        css_font = cssFont(pango_fontdesc)

        self.change_font(css_font.family,
                         css_font.weight,
                         css_font.style,
                         css_font.stretch,
                         css_font.size)

    @GtkTemplate.Callback
    def on_prev_btn(self, widget):
        self.book.docview.page_prev()

    @GtkTemplate.Callback
    def on_next_btn(self, widget):
        self.book.docview.page_next()

    @GtkTemplate.Callback
    def on_font_less(self, widget):
        self.change_fontsize(self.book.fontsize - 1)

    @GtkTemplate.Callback
    def on_font_default(self, widget):
        self.change_fontsize(self.book.fontsize_default)

    @GtkTemplate.Callback
    def on_font_more(self, widget):
        self.change_fontsize(self.book.fontsize + 1)

    @GtkTemplate.Callback
    def on_lineheight_less(self, widget):
        self.change_lineheight(self.book.lineheight - 0.2)

    @GtkTemplate.Callback
    def on_lineheight_default(self, widget):
        self.change_lineheight(self.book.lineheight_default)

    @GtkTemplate.Callback
    def on_lineheight_more(self, widget):
        self.change_lineheight(self.book.lineheight + 0.2)
