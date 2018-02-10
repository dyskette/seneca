# book.py
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
import gi

gi.require_version('Gdk', '3.0')
gi.require_version('Soup', '2.4')
gi.require_version('WebKit2', '4.0')
from gi.repository import Gdk, Gio, GLib, GObject, Soup, WebKit2
from gettext import gettext as _

from .epub import Epub
from .book_error import BookError
from .dbus_helper import DBusHelper
from .javascript import BODY_JS, WRAPPER_JS, COL_JS, COL_JS_REMOVE

logger = logging.getLogger(__name__)


class Book(WebKit2.WebView):
    __gsignals__ = {
        'scroll-percent-changed': (GObject.SIGNAL_RUN_FIRST, None, (float,)),
    }

    def __init__(self, settings):
        """Initialize Book class

        Args:
            settings (Settings)
        """
        self.settings = settings

        # Webkit context
        web_context = WebKit2.WebContext.get_default()
        web_context.set_cache_model(WebKit2.CacheModel.DOCUMENT_VIEWER)
        web_context.set_process_model(
            WebKit2.ProcessModel.MULTIPLE_SECONDARY_PROCESSES)

        # Webkit extensions
        def setup_web_extensions(context):
            application = Gio.Application.get_default()
            variant_lvl = GLib.Variant.new_int32(logger.getEffectiveLevel())
            context.set_web_extensions_directory(application.extensiondir)
            context.set_web_extensions_initialization_user_data(variant_lvl)

        web_context.connect('initialize-web-extensions', setup_web_extensions)
        web_context.register_uri_scheme('epub', self._on_epub_scheme)

        # Webkit settings
        web_settings = WebKit2.Settings()
        web_settings.set_default_font_size(self.settings.fontsize)
        web_settings.set_enable_smooth_scrolling(True)
        web_settings.set_enable_plugins(False)

        # Enable developer tools (like web inspector)
        if logger.getEffectiveLevel() <= logging.INFO:
            web_settings.set_enable_developer_extras(True)

        # Initialize
        WebKit2.WebView.__init__(self,
                                 web_context=web_context,
                                 settings=web_settings)

        # Background color of webview
        gdk_color = Gdk.Color.parse(self.settings.color_bg)
        gdk_rgba = Gdk.RGBA.from_color(gdk_color[1])
        self.set_background_color(gdk_rgba)

        # DBUS PCI
        self.dbus_helper = DBusHelper()

        # Variables
        self.doc = Epub()
        self.identifier = ''

        self.__matches_list = []
        self.__is_match_prev = False
        self.__page_turning = False

        # Signals
        self.on_reload_chapter_id = 0
        self.on_load_changed_id = self.connect('load-changed',
                                               self._on_load_change)
        self.on_decide_policy_id = self.connect('decide-policy',
                                                self._on_decide_policy)
        self.on_load_set_pos_id = 0
        self.on_load_by_fragment_id = 0
        self.on_load_by_search_id = 0
        self.on_resize_id = 0
        self.on_text_found_id = 0
        self.on_text_not_found_id = 0

    def get_doc(self):
        return self.doc

    def set_doc(self, gfile):
        """Create an Epub object using the path obtained from gfile

        Calls prepare_book() when done.

        Parameters:
            gfile (Gio.File)

        Raises:
            BookError
        """
        if self.on_reload_chapter_id:
            self.doc.disconnect(self.on_reload_chapter_id)

        try:
            path = gfile.get_path()
            if not path:
                raise BookError(0, _('Empty path!'), '')

            self.doc.open(path)
        except BookError as e:
            raise e
        else:
            self._prepare_book()

    def get_title(self):
        if self.doc.path:
            return self.doc.title
        else:
            return None

    def get_author(self):
        if self.doc.path:
            creator_list = self.doc.get_metadata('creator')
            if creator_list:
                return creator_list[0]
        else:
            return None

    def get_toc(self):
        return self.doc.get_toc()

    def get_book_position(self, chapter_position):
        current_pos = self.doc.get_current_position()
        next_pos = self.doc.get_next_position()

        if next_pos == 0.0:
            return current_pos

        percent_range = next_pos - current_pos

        if percent_range == 0.0:
            return current_pos

        percent = current_pos + (chapter_position * percent_range / 100)

        return percent

    def set_book_position(self, percent):
        positions = self.doc.get_pages_positions()

        chapter = 0
        for i in range(len(positions)):
            if percent < positions[i]:
                break
            chapter = i

        chapter_start = positions[chapter]

        if chapter == len(positions) - 1:
            chapter_end = 100.0
        else:
            chapter_end = positions[chapter + 1]

        chapter_range = chapter_end - chapter_start
        chapter_percent = (percent - chapter_start) * 100 / chapter_range

        if chapter != self.get_chapter():
            self.set_chapter(chapter)
            if not self.on_load_set_pos_id:
                self.on_load_set_pos_id = self.connect('load-changed',
                                                       self._on_load_set_pos,
                                                       chapter_percent)
        else:
            self._set_scroll_position(chapter_percent)

    def get_current_path(self):
        if self.doc.path:
            return self.doc.get_current_path()
        else:
            return None

    def get_chapter_path_fragment(self):
        # TODO: Implement function
        path = ''
        fragment = ''

        return path, fragment

    def set_chapter_path_fragment(self, path, fragment):
        """Evaluate path and fragment given to change chapter and/or position

        Args:
            path (str)
            fragment (str)
        """
        current = self.doc.get_current_path()

        if not path:
            path = current

        if not self.doc.is_page(path):
            return

        if path != current:
            self.doc.set_page_by_path(path)

        if fragment and not self.on_load_by_fragment_id:
            self.on_load_by_fragment_id = self.connect('load-changed',
                                                       self._on_load_by_fragment,
                                                       fragment)
        else:
            position = 0.0
            self.settings.save_pos(self.identifier,
                                   self.get_chapter(),
                                   position)
            self.emit('scroll-percent-changed',
                      self.get_book_position(position))

    def get_chapter(self):
        """Returns an int as chapter"""
        if self.doc.path:
            return self.doc.get_page()
        else:
            return None

    def set_chapter(self, chapter):
        """Set current chapter

        Args:
            chapter (int)
        """
        if self.doc.path:
            self.doc.set_page(chapter)

    def chapter_next(self):
        if self.doc.path:
            try:
                self.doc.go_next()
                return True
            except IndexError:
                pass

        return False

    def chapter_prev(self):
        if self.doc.path:
            try:
                self.doc.go_prev()
                return True
            except IndexError:
                pass

        return False

    def page_next(self):
        """Start DBUS call to change position to next page"""
        if (not self.doc.path
                or self.on_load_set_pos_id
                or self.on_load_by_fragment_id
                or self.on_load_by_search_id
                or self.__page_turning):
            return

        dbus_args = GLib.Variant("(ib)", (self.get_page_id(),
                                          self.settings.paginate))
        self.dbus_helper.call('ScrollNext',
                              self.get_page_id(),
                              dbus_args,
                              self._on_page_next)

    def page_prev(self):
        """Start DBUS call to change position to previous page"""
        if (not self.doc.path
                or self.on_load_set_pos_id
                or self.on_load_by_fragment_id
                or self.on_load_by_search_id
                or self.__page_turning):
            return

        dbus_args = GLib.Variant("(ib)", (self.get_page_id(),
                                          self.settings.paginate))
        self.dbus_helper.call('ScrollPrev',
                              self.get_page_id(),
                              dbus_args,
                              self._on_page_prev)

    def refresh_view(self):
        """Start the restyling of current chapter"""
        if self.doc.path:
            self._setup_view()
            position = self.settings.get_position(self.identifier)
            self._set_scroll_position(position)

    def find_text(self, search_text):
        """Start search in webview and document. Connect search signals.

        Args:
            search_text (str)
        """
        if not self.doc.path:
            return

        if not search_text:
            return

        web_find_controller = self.get_find_controller()

        if not self.on_text_found_id:
            self.on_text_found_id = web_find_controller.connect(
                'found-text',
                self._on_found_text)

        if not self.on_text_not_found_id:
            self.on_text_not_found_id = web_find_controller.connect(
                'failed-to-find-text',
                self._on_text_not_found)

        max_match_count = 1000
        web_find_controller.count_matches(search_text,
                                          WebKit2.FindOptions.CASE_INSENSITIVE,
                                          max_match_count)
        self.__matches_list = self.doc.find_text(search_text)

    def find_text_finish(self):
        """Clear the search in webview and disconnect signals."""
        if not self.__matches_list:
            return

        web_find_controller = self.get_find_controller()
        web_find_controller.search_finish()
        if self.on_text_found_id:
            web_find_controller.disconnect(self.on_text_found_id)
            self.on_text_found_id = 0
        if self.on_text_not_found_id:
            web_find_controller.disconnect(self.on_text_not_found_id)
            self.on_text_not_found_id = 0
        self.__matches_list = []

    def find_next(self):
        if not self.doc.path:
            return

        if not self.__matches_list:
            return

        web_find_controller = self.get_find_controller()
        web_find_controller.search_next()
        self.__is_match_prev = False
        self._adjust_scroll_position()

    def find_prev(self):
        if not self.doc.path:
            return

        if not self.__matches_list:
            return

        web_find_controller = self.get_find_controller()
        web_find_controller.search_previous()
        self.__is_match_prev = True
        self._adjust_scroll_position()

    # Internal functions #

    def _get_path_fragment(self, uri):
        """Use Soup.URI to split uri

        Args:
            uri (str)

        Returns:
            A list with two strings representing a path and fragment
        """
        path = None
        fragment = None

        if uri:
            soup_uri = Soup.URI.new(uri)
            path = soup_uri.get_path()[1:]
            fragment = soup_uri.get_fragment()

        return [path, fragment]

    def _on_epub_scheme(self, request):
        """Callback function for epub scheme requests

        Finish a WebKit2.URISchemeRequest by setting the contents of
        the request and its mime type.

        Args:
            request (WebKit2.URISchemeRequest)
        """
        if not self.doc:
            return

        uri = request.get_uri()

        try:
            path, fragment = self._get_path_fragment(uri)
        except BookError as e:
            error_str = e.args[1]
            request.finish_error(GLib.Error(error_str))
            return

        if self.doc.is_page(path):
            self.set_chapter_path_fragment(path, fragment)
            return

        resource_content = self.doc.get_resource_content(path)
        resource_gbytes = GLib.Bytes(resource_content)
        stream = Gio.MemoryInputStream.new_from_bytes(resource_gbytes)
        stream_length = resource_gbytes.get_size()
        mime = self.doc.get_resource_mime(path)

        request.finish(stream, stream_length, mime)

    def _on_decide_policy(self, web_view, decision, decision_type):
        """Decide what to do when clicked on link

        Args:
            web_view (WebKit2.WebView)
            decision (WebKit2.PolicyDecision)
            decision_type (WebKit2.PolicyDecisionType)

        Returns:
            True to stop other handlers from being invoked for the event.
            False to propagate the event further.
        """
        if decision_type is WebKit2.PolicyDecisionType.RESPONSE:
            response = WebKit2.ResponsePolicyDecision.get_response(decision)
            uri = response.get_uri()
            ctx = Gio.AppLaunchContext.new()
            Gio.AppInfo.launch_default_for_uri(uri, ctx)
            decision.ignore()
            return True

    def _prepare_book(self):
        """Set relevant variables for the book

        Connect to Epub 'page' property signal.
        """
        if self.doc.identifier:
            self.identifier = self.doc.identifier
        else:
            self.identifier = self.get_author() + self.get_title()

        if not self.settings.get_book(self.identifier):
            self.settings.add_book(self.identifier)

        # Chapter to resume from
        chapter = self.settings.get_chapter(self.identifier)
        self.set_chapter(chapter)
        self._reload_chapter()

        if not self.on_reload_chapter_id:
            self.on_reload_chapter_id = self.doc.connect('notify::page',
                                                         self._reload_chapter)

        if not self.on_load_set_pos_id:
            position = self.settings.get_position(self.identifier)
            self.on_load_set_pos_id = self.connect('load-changed',
                                                   self._on_load_set_pos,
                                                   position)

    def _reload_chapter(self, epub=None, paramspec=None):
        """Use Epub's page number to retrieve the resource and load it into view.

        Args:
            epub (GObject.Object)
            paramspec (GObject.ParamSpec)
        """
        resource_content = self.doc.get_current_with_epub_uris()
        resource_gbytes = GLib.Bytes(resource_content)
        mime = self.doc.get_current_mime()
        encoding = 'UTF-8'
        base_uri = None

        self.load_bytes(resource_gbytes, mime, encoding, base_uri)
        self.__page_turning = True

    def _on_load_change(self, webview, load_event):
        """If the load event has finished, call setup_view()

        Args:
            webview (WebKit2.WebView)
            load_event (WebKit2.LoadEvent)
        """
        if load_event is WebKit2.LoadEvent.FINISHED:
            self._setup_view()
            self.__page_turning = False

            if not self.on_resize_id:
                self.on_resize_id = self.connect('size-allocate',
                                                 self._on_resize)

    def _setup_view(self):
        """Run javascript with styles"""
        gdk_color = Gdk.Color.parse(self.settings.color_bg)
        gdk_rgba = Gdk.RGBA.from_color(gdk_color[1])
        self.set_background_color(gdk_rgba)

        web_settings = self.get_settings()
        web_settings.set_default_font_size(self.settings.fontsize)

        bodyjs = BODY_JS.format(bg=self.settings.color_bg,
                                fg=self.settings.color_fg)

        wrapperjs = WRAPPER_JS.format(mg=self.settings.margin,
                                      bg=self.settings.color_bg,
                                      fg=self.settings.color_fg,
                                      fs0=self.settings.fontfamily,
                                      fs1=self.settings.fontweight,
                                      fs2=self.settings.fontstyle,
                                      fs3=self.settings.fontstretch,
                                      fs4=self.settings.fontsize,
                                      lh=self.settings.lineheight)

        self.run_javascript(bodyjs)
        self.run_javascript(wrapperjs)
        if self.settings.paginate:
            self.run_javascript(COL_JS)
        else:
            self.run_javascript(COL_JS_REMOVE)

    def _on_load_set_pos(self, webview, load_event, position):
        """If the load event has finished, scroll to position

        Args:
            webview (WebKit2.WebView)
            load_event (WebKit2.LoadEvent)
        """
        if load_event is WebKit2.LoadEvent.FINISHED:
            self._set_scroll_position(position)
            self.disconnect(self.on_load_set_pos_id)
            self.on_load_set_pos_id = 0

    def _on_load_by_fragment(self, webview, load_event, fragment):
        """If the load event has finished, scroll to fragment

        Args:
            webview (WebKit2.WebView)
            load_event (WebKit2.LoadEvent)
            fragment (str)
        """
        if load_event is WebKit2.LoadEvent.FINISHED:
            self._set_scroll_to_fragment(fragment)
            self.disconnect(self.on_load_by_fragment_id)
            self.on_load_by_fragment_id = 0

    def _on_load_by_search(self, webview, load_event):
        """If the load event has finished, find the next or previous match

        Args:
            webview (WebKit2.WebView)
            load_event (WebKit2.LoadEvent)
        """
        if load_event is WebKit2.LoadEvent.FINISHED:
            if self.__is_match_prev:
                self.find_prev()
            else:
                self.find_next()
            self.disconnect(self.on_load_by_search_id)
            self.on_load_by_search_id = 0

    def _on_resize(self, webview, gdk_rectangle):
        """Call position function on every size change

        Args:
            webview (WebKit2.WebView)
            gdk_rectangle (Gdk.Rectangle)
        """
        position = self.settings.get_position(self.identifier)
        self._set_scroll_position(position)

    def _get_scroll_position(self):
        """Start DBUS call to obtain scroll position"""
        dbus_args = GLib.Variant("(ib)", (self.get_page_id(),
                                          self.settings.paginate))
        self.dbus_helper.call('GetScrollPosition',
                              self.get_page_id(),
                              dbus_args,
                              self._on_get_scroll_position)

    def _on_get_scroll_position(self, source, result):
        """Obtain scroll position and save it

        Args:
            source (GObject.Object)
            result (Gio.AsyncResult)
        """
        try:
            position = source.call_finish(result)[0]
        except Exception as e:
            logger.error('On get position:' + str(e))
        else:
            self.settings.save_pos(self.identifier,
                                   self.get_chapter(),
                                   position)
            self.emit('scroll-percent-changed',
                      self.get_book_position(position))

    def _set_scroll_position(self, position):
        """Start DBUS call to set scroll position

        Args:
            position (float)
        """
        dbus_args = GLib.Variant("(ibd)", (self.get_page_id(),
                                           self.settings.paginate,
                                           position))
        self.dbus_helper.call('SetScrollPosition',
                              self.get_page_id(),
                              dbus_args,
                              self._on_set_scroll_position)

    def _on_set_scroll_position(self, source, result):
        """Obtain result to set position

        Args:
            source (GObject.Object)
            result (Gio.AsyncResult)
        """
        try:
            position_changed = source.call_finish(result)[0]
        except Exception as e:
            logger.error('On set position:' + str(e))
        else:
            if position_changed:
                self._get_scroll_position()
            else:
                logger.warning('Could not set position:Unknown')

    def _set_scroll_to_fragment(self, fragment):
        """Start DBUS call to set scroll position to an element id

        Args:
            fragment (str)
        """
        dbus_args = GLib.Variant("(ibs)", (self.get_page_id(),
                                           self.settings.paginate,
                                           fragment))
        self.dbus_helper.call('SetScrollToFragment',
                              self.get_page_id(),
                              dbus_args,
                              self._on_set_scroll_to_fragment)

    def _on_set_scroll_to_fragment(self, source, result):
        """Obtain result to fragment position

        Args:
            source (GObject.Object)
            result (Gio.AsyncResult)
        """
        try:
            position_changed = source.call_finish(result)[0]
        except Exception as e:
            logger.error('Scroll to fragment:' + str(e))
        else:
            if position_changed:
                self._get_scroll_position()
            else:
                logger.warning('Could not set position to fragment:Unknown')

    def _on_page_next(self, source, result):
        """Obtain result to page next position

        Args:
            source (GObject.Object)
            result (Gio.AsyncResult)
        """
        try:
            position_changed = source.call_finish(result)[0]
        except Exception as e:
            logger.error('Page Next:' + str(e))
            return

        if position_changed:
            self._get_scroll_position()
            return

        chapter_switched = self.chapter_next()
        if not chapter_switched:
            return

        if not self.on_load_set_pos_id:
            position = 0.0
            self.on_load_set_pos_id = self.connect('load-changed',
                                                   self._on_load_set_pos,
                                                   position)

    def _on_page_prev(self, source, result):
        """Obtain result to page previous position

        Args:
            source (GObject.Object)
            result (Gio.AsyncResult)
        """
        try:
            position_changed = source.call_finish(result)[0]
        except Exception as e:
            logger.error('Page Previous:' + str(e))
            return

        if position_changed:
            self._get_scroll_position()
            return

        chapter_switched = self.chapter_prev()
        if not chapter_switched:
            return

        if not self.on_load_set_pos_id:
            position = 100.0
            self.on_load_set_pos_id = self.connect('load-changed',
                                                   self._on_load_set_pos,
                                                   position)

    def _adjust_scroll_position(self):
        """Start DBUS call to adjust scroll position"""
        dbus_args = GLib.Variant("(ib)", (self.get_page_id(),
                                          self.settings.paginate))
        self.dbus_helper.call('AdjustScrollPosition',
                              self.get_page_id(),
                              dbus_args,
                              self._on_adjust_scroll_position)

    def _on_adjust_scroll_position(self, source, result):
        """Obtain result to adjust scroll position

        Args:
            source (GObject.Object)
            result (Gio.AsyncResult)
        """
        try:
            position_changed = source.call_finish(result)[0]
        except Exception as e:
            logger.error('Adjust scroll position:' + str(e))
        else:
            if position_changed:
                self._get_scroll_position()

    def _on_found_text(self, web_find_controller, match_count):
        """Fix position because web_find_controller centers the match.

        Args:
            web_find_controller (WebKit2.FindController)
            match_count (int)
        """
        self._get_scroll_position()

    def _on_text_not_found(self, web_find_controller):
        """Change to chapter that contains a match when not match is found on
        WebView on search, next or previous.

        Args:
             web_find_controller (WebKit2.FindController)
        """
        search_text = web_find_controller.get_search_text()
        if not search_text or not self.__matches_list:
            return

        chapter = self.get_chapter()
        path = None

        # FIXME: WebKit2.FindController sometimes misses a match in WebView.
        # I don't know if it's because it only searches forward by default.

        if self.__is_match_prev:
            ordered_matches = self.__matches_list[:chapter][::-1] + \
                              self.__matches_list[chapter:][::-1]
        else:
            ordered_matches = self.__matches_list[chapter + 1:] + \
                              self.__matches_list[:chapter + 1]

        for i in range(len(ordered_matches)):
            if ordered_matches[i][1]:
                path = ordered_matches[i][0]
                break

        if path is not None and path != self.doc.get_current_path():
            self.doc.set_page_by_path(path)
            if not self.on_load_by_search_id:
                if self.__is_match_prev and not self.on_load_set_pos_id:
                    position = 100.0
                    self.on_load_set_pos_id = self.connect('load-changed',
                                                           self._on_load_set_pos,
                                                           position)
                self.on_load_by_search_id = self.connect('load-changed',
                                                         self._on_load_by_search)
        else:
            logger.info('No coincidences in epub')
