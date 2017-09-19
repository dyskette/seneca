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

import logging
logger = logging.getLogger(__name__)

import gi
gi.require_version('Gdk', '3.0')
gi.require_version('Gtk', '3.0')
from gi.repository import Gdk, Gtk, Gio, GLib

from .gi_composites import GtkTemplate
from .book import Book
from .book_error import BookError
from .font import pangoFontDesc, cssFont
from .settings import Settings
from .toc import Toc

@GtkTemplate(ui='/com/github/dyskette/Seneca/ui/window.ui')
class ApplicationWindow(Gtk.ApplicationWindow):
    __gtype_name__ = 'ApplicationWindow'

    header_bar = GtkTemplate.Child()
    open_menu = GtkTemplate.Child()
    toc_btn = GtkTemplate.Child()
    grid_sidebar = GtkTemplate.Child()
    toc_treeview = GtkTemplate.Child()
    toc_treestore = GtkTemplate.Child()
    main_popover = GtkTemplate.Child()
    book_view = GtkTemplate.Child()
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
        self.application = application
        self.init_template()
        self.settings = Settings()
        self.book = Book(self.settings)
        self.book_toc = Toc(self.book, self.toc_treeview, self.toc_treestore)
        self.gtk_settings = Gtk.Settings.get_default()

        variant = GLib.Variant('s', self.settings.color)
        color_action = Gio.SimpleAction.new_stateful('color', variant.get_type(), variant)
        color_action.connect('change-state', self.change_color)
        self.add_action(color_action)

        # Sync UI with settings
        self.set_default_size(self.settings.width, self.settings.height)
        if self.settings.maximized:
            self.maximize()
        self.change_window_color(self.settings.color)
        self.refresh_font_button()
        self.refresh_fontsize_label()
        self.refresh_lineheight_label()

        # Initialize with headerbar buttons disabled
        self.prev_btn.set_sensitive(False)
        self.next_btn.set_sensitive(False)
        # self.open_menu.set_sensitive(False)

        # Drag and drop
        # Unset webview as a drop destination
        self.book.drag_dest_unset()

        # FIXME: Window raises on drop event. Why?
        self.uri_list = 11
        targets = [Gtk.TargetEntry.new('text/uri-list', 0, self.uri_list)]
        self.grid.drag_dest_set(Gtk.DestDefaults.ALL,
                                targets,
                                Gdk.DragAction.COPY)
        self.grid.connect('drag-data-received', self.on_drag_data_received)

        self.book_view.pack_end(self.book, True, True, 0)
        self.book_view.show_all()

        self.connect('size-allocate', self.on_size_allocate)

    def open_file(self, _gfile):
        try:
            self.book.set_doc(_gfile)
        except BookError as e:
            logger.error('Book couldn\'t be opened: {}'.format(e))
            #TODO: Use an application notification.
        else:
            self.book_toc.populate_store()
            self.toc_btn.set_active(True)
            self.grid_sidebar.set_visible(True)

            self.header_bar.set_title(self.book.get_title())
            self.header_bar.set_subtitle(self.book.get_author())

            # Make headerbar buttons available
            self.prev_btn.set_sensitive(True)
            self.next_btn.set_sensitive(True)

    def change_window_color(self, color):
        dark = self.gtk_settings.get_property('gtk-application-prefer-dark-theme')

        if color == 'dark' and not dark:
            self.gtk_settings.set_property('gtk-application-prefer-dark-theme', True)
        elif color in ('light', 'sepia') and dark:
            self.gtk_settings.set_property('gtk-application-prefer-dark-theme', False)

    def refresh_font_button(self):
        pango_font_desc = pangoFontDesc(self.settings.fontfamily,
                                        self.settings.fontweight,
                                        self.settings.fontstyle,
                                        self.settings.fontstretch,
                                        self.settings.fontsize)
        self.font_btn.set_font_desc(pango_font_desc)

    def refresh_fontsize_label(self):
        fontsize = self.settings.fontsize

        self.font_less.set_sensitive(fontsize > 8)
        self.font_more.set_sensitive(fontsize < 32)

        fs_label = '{0}px'.format(fontsize)
        self.font_label.set_label(fs_label)

    def refresh_lineheight_label(self):
        lineheight = self.settings.lineheight

        self.lineheight_less.set_sensitive(lineheight > 1.0)
        self.lineheight_more.set_sensitive(lineheight < 2.8)

        lh_label = '{0}pt'.format(lineheight)
        self.lineheight_label.set_label(lh_label)

    def change_color(self, action, value):
        color = value.get_string()

        self.change_window_color(color)

        self.settings.color = color
        self.book.set_settings(self.settings)

        action.set_state(value)

    def change_fontsize(self, fontsize):
        self.settings.fontsize = fontsize
        self.book.set_settings(self.settings)

        self.refresh_fontsize_label()
        self.refresh_font_button()

    def change_lineheight(self, lineheight):
        lineheight = float(format(lineheight, '1.2f'))

        self.settings.lineheight = lineheight
        self.book.set_settings(self.settings)

        self.refresh_lineheight_label()

    @GtkTemplate.Callback
    def on_font_set(self, widget):
        pango_font_desc = widget.get_property('font-desc')
        css_font = cssFont(pango_font_desc)

        self.settings.fontfamily = css_font['family']
        self.settings.fontweight = css_font['weight']
        self.settings.fontstyle = css_font['style']
        self.settings.fontstretch = css_font['stretch']
        self.settings.fontsize = css_font['size']

        self.book.set_settings(self.settings)

        self.refresh_fontsize_label()

    @GtkTemplate.Callback
    def on_prev_btn(self, widget):
        self.book.page_prev()

    @GtkTemplate.Callback
    def on_next_btn(self, widget):
        self.book.page_next()

    @GtkTemplate.Callback
    def on_font_less(self, widget):
        self.change_fontsize(self.settings.fontsize - 1)

    @GtkTemplate.Callback
    def on_font_default(self, widget):
        fs_default = int(self.settings.default['fontsize'])
        self.change_fontsize(fs_default)

    @GtkTemplate.Callback
    def on_font_more(self, widget):
        self.change_fontsize(self.settings.fontsize + 1)

    @GtkTemplate.Callback
    def on_lineheight_less(self, widget):
        self.change_lineheight(self.settings.lineheight - 0.2)

    @GtkTemplate.Callback
    def on_lineheight_default(self, widget):
        lh_default = float(self.settings.default['lineheight'])
        self.change_lineheight(lh_default)

    @GtkTemplate.Callback
    def on_lineheight_more(self, widget):
        self.change_lineheight(self.settings.lineheight + 0.2)

    @GtkTemplate.Callback
    def on_toc_btn_toggled(self, widget):
        visible = self.grid_sidebar.get_visible()
        self.grid_sidebar.set_visible(not visible)

    @GtkTemplate.Callback
    def on_search_btn_toggled(self, widget):
        pass

    def on_size_allocate(self, window, gdk_rectangle):
        self.settings.maximized = self.is_maximized()
        if not self.is_maximized():
            self.settings.width , self.settings.height = self.get_size()

    def on_drag_data_received(self, widget, context, x, y, data, info, time):
        logger.info('Drag data received')

        if info == self.uri_list:
            uris = data.get_uris()
            if uris:
                files = []
                for uri in uris:
                    if uri.startswith('file://'):
                        files.append(Gio.File.new_for_uri(uri))

                self.application.open(files, '')

        context.finish(True, False, time)
