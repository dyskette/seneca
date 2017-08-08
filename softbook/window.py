# window.py
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

        variant = GLib.Variant('s', 'light')
        self.color_action = Gio.SimpleAction.new_stateful('color', variant.get_type(), variant)
        self.color_action.connect('change-state', self.on_change_color)
        self.add_action(self.color_action)

        # Initialize with headerbar buttons disabled
        self.prev_btn.set_sensitive(False)
        self.next_btn.set_sensitive(False)
        self.open_menu.set_sensitive(False)

    def open_file(self, _gfile):
        try:
            self.book = Book(_gfile)
            # Add to view
            self.main_view.pack_start(self.book, True, True, 0)
            self.book.show_all()

            # Make headerbar buttons available
            self.prev_btn.set_sensitive(True)
            self.next_btn.set_sensitive(True)
            self.open_menu.set_sensitive(True)

            # Sync buttons with settings
            _font = self.book.get_font()
            pango_font = pangoFont(_font[0], _font[1], _font[2], _font[3], _font[4])
            self.font_btn.set_font_desc(pango_font.desc)

            self.font_label.set_label('{0}px'.format(self.book.get_fontsize()))
            self.lineheight_label.set_label('{0}pt'.format(self.book.get_lineheight()))

            variant = GLib.Variant('s', self.book.get_color())
            self.color_action.set_state(variant)
        except Exception as e:
            raise ValueError(e)
            #TODO: Use an application notification.

    def change_fontsize(self, fontsize):
        self.book.set_fontsize(fontsize)
        self.font_less.set_sensitive(fontsize > 8)
        self.font_more.set_sensitive(fontsize < 32)
        self.font_label.set_label('{0}px'.format(self.book.get_fontsize()))

    def change_lineheight(self, lineheight):
        self.book.set_lineheight(float(format(lineheight, '1.2f')))
        self.lineheight_less.set_sensitive(lineheight > 1.0)
        self.lineheight_more.set_sensitive(lineheight < 2.8)
        self.lineheight_label.set_label('{0}pt'.format(self.book.get_lineheight()))

    def on_change_color(self, action, value):
        action.set_state(value)
        self.book.set_color(value.get_string())

    @GtkTemplate.Callback
    def on_font_set(self, widget):
        pango_fontdesc = widget.get_property('font-desc')
        css_font = cssFont(pango_fontdesc)

        self.book.set_font([css_font.family,
                            css_font.weight,
                            css_font.style,
                            css_font.stretch,
                            css_font.size])

    @GtkTemplate.Callback
    def on_prev_btn(self, widget):
        self.book.page_prev()

    @GtkTemplate.Callback
    def on_next_btn(self, widget):
        self.book.page_next()

    @GtkTemplate.Callback
    def on_font_less(self, widget):
        self.change_fontsize(self.book.get_fontsize() - 1)

    @GtkTemplate.Callback
    def on_font_default(self, widget):
        self.change_fontsize(20)

    @GtkTemplate.Callback
    def on_font_more(self, widget):
        self.change_fontsize(self.book.get_fontsize() + 1)

    @GtkTemplate.Callback
    def on_lineheight_less(self, widget):
        self.change_lineheight(self.book.get_lineheight() - 0.2)

    @GtkTemplate.Callback
    def on_lineheight_default(self, widget):
        self.change_lineheight(1.6)

    @GtkTemplate.Callback
    def on_lineheight_more(self, widget):
        self.change_lineheight(self.book.get_lineheight() + 0.2)
