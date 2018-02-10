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

from gettext import gettext as _

import gi

gi.require_version('Gdk', '3.0')
gi.require_version('Gtk', '3.0')
from gi.repository import Gdk, Gtk, Gio, GLib, GObject

from .gi_composites import GtkTemplate
from .book import Book
from .book_error import BookError
from .dialogs import FileChooserDialog
from .font import pangoFontDesc, cssFont
from .settings import Settings
from .toc import TocDialog

TIMEOUT_REVEALER = 500


@GtkTemplate(ui='/com/github/dyskette/Seneca/ui/window.ui')
class ApplicationWindow(Gtk.ApplicationWindow):
    __gtype_name__ = 'ApplicationWindow'

    header_bar = GtkTemplate.Child()
    open_menu = GtkTemplate.Child()
    toc_btn = GtkTemplate.Child()
    grid = GtkTemplate.Child()
    main_popover = GtkTemplate.Child()
    infobar = GtkTemplate.Child()
    infobar_lbl_title = GtkTemplate.Child()
    infobar_lbl_msg = GtkTemplate.Child()
    book_view = GtkTemplate.Child()
    font_btn = GtkTemplate.Child()
    font_less = GtkTemplate.Child()
    font_default = GtkTemplate.Child()
    font_more = GtkTemplate.Child()
    font_label = GtkTemplate.Child()
    lineheight_less = GtkTemplate.Child()
    lineheight_default = GtkTemplate.Child()
    lineheight_more = GtkTemplate.Child()
    lineheight_label = GtkTemplate.Child()
    search_btn = GtkTemplate.Child()
    search_bar = GtkTemplate.Child()
    search_entry = GtkTemplate.Child()
    search_prev_btn = GtkTemplate.Child()
    search_next_btn = GtkTemplate.Child()
    open_btn = GtkTemplate.Child()
    overlay_controls = GtkTemplate.Child()
    bottom_revealer = GtkTemplate.Child()
    prev_btn_revealer = GtkTemplate.Child()
    next_btn_revealer = GtkTemplate.Child()
    bottom_scale = GtkTemplate.Child()
    scale_label = GtkTemplate.Child()
    prev_btn = GtkTemplate.Child()
    next_btn = GtkTemplate.Child()
    progress_adjustment = GtkTemplate.Child()

    def __init__(self, application):
        Gtk.ApplicationWindow.__init__(self, application=application)
        self.application = application
        self.init_template()
        self.settings = Settings()
        self.book = Book(self.settings)
        self.gtk_settings = Gtk.Settings.get_default()
        self.overlay_timeout_source = None

        color_variant = GLib.Variant.new_string(self.settings.color)
        color_action = Gio.SimpleAction.new_stateful('color',
                                                     color_variant.get_type(),
                                                     color_variant)
        color_action.connect('change-state', self.change_color)
        self.add_action(color_action)

        paginate_variant = GLib.Variant.new_boolean(self.settings.paginate)
        paginate_action = Gio.SimpleAction.new_stateful('paginate',
                                                        None,
                                                        paginate_variant)
        paginate_action.connect('change-state', self.change_paginate)
        self.add_action(paginate_action)

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
        self.toc_btn.set_sensitive(False)
        self.search_btn.set_sensitive(False)
        self.open_menu.set_sensitive(False)

        self.search_btn.bind_property('active',
                                      self.search_bar,
                                      'search-mode-enabled',
                                      GObject.BindingFlags.BIDIRECTIONAL)
        self.search_bar.connect('notify::search-mode-enabled',
                                self.on_search_mode_enabled)

        # Drag and drop
        # Unset webview as a drop destination
        self.book.drag_dest_unset()

        self.uri_list = 11
        targets = [Gtk.TargetEntry.new('text/uri-list', 0, self.uri_list)]
        self.grid.drag_dest_set(Gtk.DestDefaults.ALL,
                                targets,
                                Gdk.DragAction.COPY)

        self.overlay_controls.add_events(Gdk.EventMask.ENTER_NOTIFY_MASK)

        self.grid.connect('drag-data-received', self.on_drag_data_received)

        self.book.connect('scroll-event', self.on_scroll_event)
        self.book.connect('key-press-event', self.on_book_key_press_event)
        self.book.connect('scroll-percent-changed',
                          self.on_scroll_percent_changed)

        self.book_view.connect('motion-notify-event',
                               self.on_motion_notify_event)
        self.book_view.pack_end(self.book, True, True, 0)
        self.book_view.show_all()

        self.connect('key-press-event', self.on_key_press_event)
        self.connect('size-allocate', self.on_size_allocate)

    def open_file(self, _gfile):
        try:
            self.book.set_doc(_gfile)
        except BookError as e:
            self.show_infobar(e)
        else:
            self.header_bar.set_title(self.book.get_title())
            self.header_bar.set_subtitle(self.book.get_author())

            # Make headerbar buttons available
            self.prev_btn.set_sensitive(True)
            self.next_btn.set_sensitive(True)
            self.toc_btn.set_sensitive(True)
            self.search_btn.set_sensitive(True)
            self.open_menu.set_sensitive(True)

    def show_infobar(self, error):
        error_code = error.args[0]
        error_message = error.args[1]
        epub_path = error.args[2]

        if error_code == 0:
            self.infobar_lbl_title.set_text(
                _('Could not load book') + ' «' + epub_path + '»')
            self.infobar_lbl_title.show()
        elif error_code == 1:
            self.infobar_lbl_title.hide()

        self.infobar_lbl_msg.set_text(error_message)
        self.infobar.show()

    def change_window_color(self, color):
        dark_theme = 'gtk-application-prefer-dark-theme'
        dark = self.gtk_settings.get_property(dark_theme)

        if color == 'dark' and not dark:
            self.gtk_settings.set_property(dark_theme, True)
        elif color in ('light', 'sepia') and dark:
            self.gtk_settings.set_property(dark_theme, False)

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
        self.book.refresh_view()
        action.set_state(value)

    def change_paginate(self, action, value):
        paginate = value.get_boolean()
        self.settings.paginate = paginate
        self.book.refresh_view()
        action.set_state(value)

    def change_fontsize(self, fontsize):
        self.settings.fontsize = fontsize
        self.book.refresh_view()

        self.refresh_fontsize_label()
        self.refresh_font_button()

    def change_lineheight(self, lineheight):
        lineheight = float(format(lineheight, '1.2f'))

        self.settings.lineheight = lineheight
        self.book.refresh_view()

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

        self.book.refresh_view()

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
    def on_toc_btn_clicked(self, widget):
        chapter_path, fragment = self.book.get_chapter_path_fragment()
        toc_list = self.book.get_toc()
        toc_dialog = TocDialog(self)

        toc_dialog.populate_store(toc_list)
        toc_dialog.select_active_chapter(chapter_path, fragment)
        toc_dialog.connect('toc-item-activated',
                           self.on_toc_item_activated)
        toc_dialog.run()
        toc_dialog.destroy()

    @GtkTemplate.Callback
    def on_infobar_btn_clicked(self, widget):
        self.infobar.hide()

    def on_search_mode_enabled(self, widget, paramspec):
        search_mode = self.search_bar.get_search_mode()
        if search_mode:
            search_text = self.search_entry.get_text()
            self.book.find_text(search_text)
            self.search_entry.grab_focus()
        else:
            self.book.find_text_finish()
            self.book.grab_focus()

    @GtkTemplate.Callback
    def on_search_changed(self, widget):
        search_text = self.search_entry.get_text()
        self.book.find_text(search_text)

    @GtkTemplate.Callback
    def on_stop_search(self, widget):
        self.search_bar.set_search_mode(False)

    @GtkTemplate.Callback
    def on_search_next(self, widget):
        self.book.find_next()

    @GtkTemplate.Callback
    def on_search_prev(self, widget):
        self.book.find_prev()

    def on_size_allocate(self, window, gdk_rectangle):
        self.settings.maximized = self.is_maximized()
        if not self.is_maximized():
            self.settings.width, self.settings.height = self.get_size()

    def on_scroll_event(self, widget, event):
        """Handles scroll on webview

        Args:
            widget (Gtk.Widget)
            event (Gdk.EventScroll)

        Returns:
            True to stop other handlers from being invoked for the event.
        """
        if event.delta_y > 0.5:
            self.book.page_next()
        elif event.delta_y < -0.5:
            self.book.page_prev()

        return True

    def on_book_key_press_event(self, widget, event):
        """Handles key presses on webview

        Args:
            widget (Gtk.Widget)
            event (Gdk.EventKey)

        Returns:
            True to stop other handlers from being invoked for the event.
        """
        if (event.keyval == Gdk.KEY_Left or
            event.keyval == Gdk.KEY_Up or
            event.keyval == Gdk.KEY_Page_Up or
            (event.state and event.state == Gdk.ModifierType.SHIFT_MASK and
             event.keyval == Gdk.KEY_space)):
            self.book.page_prev()
            return True
        elif (event.keyval == Gdk.KEY_Right or
              event.keyval == Gdk.KEY_Down or
              event.keyval == Gdk.KEY_Page_Down or
              event.keyval == Gdk.KEY_space):
            self.book.page_next()
            return True

        return False

    def on_key_press_event(self, widget, event):
        """Handles key presses

        Args:
            widget (Gtk.Widget)
            event (Gdk.EventKey)

        Returns:
            True to stop other handlers from being invoked for the event.
        """
        if (event.state
                and event.state == Gdk.ModifierType.CONTROL_MASK
                and event.keyval == Gdk.KEY_f):
            self.search_bar.set_search_mode(True)
            self.search_entry.grab_focus()
            return True

        if (event.state
                and event.state == Gdk.ModifierType.CONTROL_MASK
                and event.keyval == Gdk.KEY_g):
            self.book.find_next()
            return True

        if (event.state
                and event.state == Gdk.ModifierType.SHIFT_MASK | Gdk.ModifierType.CONTROL_MASK
                and event.keyval == Gdk.KEY_G):
            self.book.find_prev()
            return True

        return False

    @GtkTemplate.Callback
    def on_open_btn(self, widget):
        file_chooser = FileChooserDialog(self.application.get_active_window())
        response = file_chooser.run()
        if response == Gtk.ResponseType.OK:
            file_uri = file_chooser.get_uri()
            if file_uri:
                gfile = [Gio.File.new_for_uri(file_uri)]
                self.application.open(gfile, '')

        file_chooser.destroy()

    def on_drag_data_received(self, widget, context, x, y, data, info, time):

        if info == self.uri_list:
            uris = data.get_uris()
            if uris:
                files = []
                for uri in uris:
                    if uri.startswith('file://'):
                        files.append(Gio.File.new_for_uri(uri))

                self.application.open(files, '')

        context.finish(True, False, time)

    def on_motion_notify_event(self, grid, event_motion):
        """
        When the mouse moves on top of the grid, we show the children of the
        revealers

        Args:
            grid (Gtk.Box)
            event_motion (Gdk.EventMotion)
        """
        if not self.bottom_revealer.get_reveal_child():
            self.bottom_revealer.set_reveal_child(True)
            self.prev_btn_revealer.set_reveal_child(True)
            self.next_btn_revealer.set_reveal_child(True)

        self.set_overlay_timeout()

        return True

    def clear_timeout_overlay_source(self):
        """
        Remove the source timeout object

        """
        if self.overlay_timeout_source:
            self.overlay_timeout_source.unref()
            self.overlay_timeout_source.destroy()

        self.overlay_timeout_source = None

    def set_overlay_timeout(self):
        """
        Create a timeout source object that will call another function when
        it runs out of time.

        """
        self.clear_timeout_overlay_source()

        source = GLib.timeout_source_new(1000)
        source.set_callback(self.on_overlay_timeout, None)
        source.attach(None)

        self.overlay_timeout_source = source

    def on_overlay_timeout(self, data):
        """
        Callback function that hides the revealer's children on the overlay

        :param data:
        :return: False to keep spreading the event
        """
        self.bottom_revealer.set_reveal_child(False)
        self.prev_btn_revealer.set_reveal_child(False)
        self.next_btn_revealer.set_reveal_child(False)

        self.clear_timeout_overlay_source()

        return False

    @GtkTemplate.Callback
    def on_overlay_controls_enter_notify_event(self, overlay, event):
        """
        The ::enter-notify-event will be emitted when the pointer enters
        the widget’s window.

        :type overlay: Gtk.Overlay
        :type event: Gdk.EventCrossing

        :return: False to keep spreading the event
        """
        self.clear_timeout_overlay_source()

        return False

    def on_scroll_percent_changed(self, book, percent):
        self.progress_adjustment.set_value(percent)

    @GtkTemplate.Callback
    def on_bottom_scale_change_value(self, range, scroll, value):
        """
        Callback function to adjust position on book by the given
        value of the range based object

        :type range: Gtk.Range
        :type scroll: Gtk.ScrollType
        :type value: float

        :return: False to keep spreading the event
        """
        self.book.set_book_position(value)

        return False

    @GtkTemplate.Callback
    def on_bottom_scale_value_changed(self, range):
        """
        Callback function when the value of GtkScale changed

        :param range: The Gtk.Range object that triggered the event
        """
        self.scale_label.set_label(str('%.1f' % range.get_value()) + ' %')

    def on_toc_item_activated(self, toc_dialog, path, fragment):
        self.book.set_chapter_path_fragment(path, fragment)
        toc_dialog.destroy()
