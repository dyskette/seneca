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
logger = logging.getLogger(__name__)

import gi
gi.require_version('Gdk', '3.0')
gi.require_version('Soup', '2.4')
gi.require_version('WebKit2', '4.0')
from gi.repository import Gdk, Gio, GLib, Soup, WebKit2

from .epub import Epub
from .book_error import BookError

BODY_JS = '''
document.body.style.backgroundColor = '{bg}';
document.body.style.color = '{fg}';
document.body.style.margin = '0px';
'''

WRAPPER_JS = '''
var wrapper = document.getElementById('SenecaInnerWrapper');

wrapper.style.backgroundColor = '{bg}';
wrapper.style.color = '{fg}';
wrapper.style.margin = '0px {mg}px 0px {mg}px';
wrapper.style.fontFamily = '{fs0}';
wrapper.style.fontWeight = '{fs1}';
wrapper.style.fontStyle = '{fs2}';
wrapper.style.fontStretch = '{fs3}';
wrapper.style.fontSize = '{fs4}px';
wrapper.style.lineHeight = '{lh}';
'''

COL_JS_INNER = '''
function resizeColumn() {
    console.log('resizeColumn was called');
    if (window.innerWidth < 800) {
        console.log('View width less than 800');
        document.body.style.columnWidth = window.innerWidth + 'px';
        document.body.style.height = (window.innerHeight - 40) + 'px';
        console.log('Column width is ' + window.innerWidth + 'px');
    }
    else {
        console.log('View width equal or more than 800');
        document.body.style.columnWidth = Math.floor(window.innerWidth / 2) + 'px';
        document.body.style.height = (window.innerHeight - 40) + 'px';
        document.body.style.columnCount = '2';
        console.log('Column width is ' + Math.floor(window.innerWidth / 2) + 'px');
    }
}
resizeColumn();
window.addEventListener('resize', resizeColumn);
'''

COL_JS = '''
if (!document.getElementById('columnJS')) {{
    var child_script = document.createElement('script');
    child_script.type = 'text/javascript';
    child_script.id = 'columnJS'
    child_script.innerHTML = `{0}`;
    document.body.appendChild(child_script);
}}
document.body.style.margin = '20px 0px 20px 0px';
document.body.style.columnGap = '0px';
'''.format(COL_JS_INNER)

COL_JS_REMOVE = '''
if (document.getElementById('columnJS')) {
    document.body.style.columnWidth = 'auto';
    document.body.style.height = 'auto';
    document.body.style.columnCount = 'auto';
    document.body.style.overflow = 'auto';
    document.body.style.margin = 'auto';
    document.body.style.columnGap = 'auto';
    document.body.removeChild(document.getElementById('columnJS'));
}
'''

class DBusHelper:

    def __init__(self):
        self.signals = {}
        application = Gio.Application.get_default()
        self.bus_conn = application.get_dbus_connection()
        self.bus_path = '/com/github/dyskette/Seneca/Paginate'
        self.bus_name = 'com.github.dyskette.Seneca.Paginate'

    def call(self, call, dbus_args, callback, page_id, *args):
        """Create proxy to access method

        Args:
            call (str)
            dbus_args (GLib.Variant or None)
            callback (function)
            page_id (int)
        """
        try:
            page_bus_name = self.bus_name + '.Page%s' % page_id
            Gio.DBusProxy.new(self.bus_conn,
                              Gio.DBusProxyFlags.NONE,
                              None,
                              page_bus_name,
                              self.bus_path,
                              self.bus_name,
                              None,
                              self.__on_get_proxy,
                              call,
                              dbus_args,
                              callback,
                              *args)
        except Exception as e:
            logger.error("DBusHelper::call():", e)

    def connect(self, signal, callback, page_id):
        """Connect callback to object signals

        Args:
            signal (str)
            callback (function)
            page_id (int)
        """
        try:
            bus = El().get_dbus_connection()
            proxy_bus = PROXY_BUS % page_id
            subscribe_id = bus.signal_subscribe(None, proxy_bus, signal,
                                                PROXY_PATH, None,
                                                Gio.DBusSignalFlags.NONE,
                                                callback)
            self.__signals[page_id] = (bus, subscribe_id)
        except Exception as e:
            print("DBusHelper::connect():", e)

    def disconnect(self, page_id):
        """Disconnect signal

        Args:
            page_id (int)
        """
        if page_id in self.__signals.keys():
            (bus, subscribe_id) = self.__signals[page_id]
            bus.signal_unsubscribe(subscribe_id)
            del self.__signals[page_id]

    def __on_get_proxy(self, source, result, call, dbus_args, callback, *args):
        """Launch call and connect it to callback

        Args:
            source (GObject.Object) - Gio.DBusProxy which started this function
            result (Gio.AsyncResult)
            call (str)
            dbus_args (GLib.Variant or None)
            callback (function)
        """
        try:
            proxy = source.new_finish(result)
            proxy.call(call,
                       dbus_args,
                       Gio.DBusCallFlags.NO_AUTO_START,
                       1000,
                       None,
                       callback,
                       *args)
        except Exception as e:
            logger.error("DBusHelper::__on_get_proxy():", e)

class Book(WebKit2.WebView):

    def __init__(self, settings):
        """Initialize Book class

        Args:
            settings (Settings)
        """
        self.settings = settings

        # Webkit context
        web_context = WebKit2.WebContext.get_default()
        web_context.set_cache_model(WebKit2.CacheModel.DOCUMENT_VIEWER)
        web_context.set_process_model(WebKit2.ProcessModel.MULTIPLE_SECONDARY_PROCESSES)

        # Webkit extensions
        def setup_web_extensions(context):
            application = Gio.Application.get_default()
            variant_lvl = GLib.Variant.new_int32(logger.getEffectiveLevel())
            context.set_web_extensions_directory(application.extensiondir)
            context.set_web_extensions_initialization_user_data(variant_lvl)

        web_context.connect('initialize-web-extensions', setup_web_extensions)
        web_context.register_uri_scheme('epub', self.on_epub_scheme)

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
        self.doc = None
        self.identifier = None

        self.__matches_list = None
        self.__is_match_prev = False
        self.__page_turning = False

        # Signals
        self.on_reload_chapter_id = None
        self.on_load_changed_id = self.connect('load-changed', self.on_load_change)
        self.on_decide_policy_id = self.connect('decide-policy', self.on_decide_policy)
        self.on_load_set_pos_id = None
        self.on_load_by_fragment_id = None
        self.on_load_by_search_id = None
        self.on_resize_id = None
        self.on_text_found_id = None
        self.on_text_not_found_id = None

    def get_path_fragment(self, uri):
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

    def jump_to_path_fragment(self, path, fragment):
        """Evaluate path and fragment given to change chapter and/or position

        Args:
            path (str)
            fragment (str)

        Returns:
            A boolean depending if the operation was succesful or not
        """
        current = self.doc.get_current_path()

        if not path:
            path = current

        if not self.doc.is_navigation_type(path):
            return False

        if path == current:
            logger.info('Same chapter')
            if fragment:
                self.set_scroll_to_fragment(fragment)
            return True
        else:
            logger.info('Changing chapter')
            self.doc.set_page_by_path(path)
            if fragment:
                if self.on_load_by_fragment_id is None:
                    self.on_load_by_fragment_id = self.connect('load-changed',
                                                               self.on_load_by_fragment,
                                                               fragment)
            else:
                position = 0.0
                self.settings.save_pos(self.identifier,
                                       self.get_chapter(),
                                       position)
            return True

        return False

    def on_epub_scheme(self, request):
        """Callback function for epub scheme requests

        Finish a WebKit2.URISchemeRequest by setting the contents of the request
        and its mime type.

        Args:
            request (WebKit2.URISchemeRequest)
        """
        if not self.doc:
            return

        uri = request.get_uri()
        logger.info('Resource request:' + uri)
        try:
            path, fragment = self.get_path_fragment(uri)
            if self.jump_to_path_fragment(path, fragment):
                return
        except BookError as e:
            error_str = str(e)
            logger.error('Could not get resource:' + error_str)
            request.finish_error(GLib.Error(error_str))
        else:
            bytes = self.doc.get_resource(path)
            gbytes = GLib.Bytes(bytes)
            stream = Gio.MemoryInputStream.new_from_bytes(gbytes)
            stream_length = gbytes.get_size()
            mime = self.doc.get_resource_mime(path)

            request.finish(stream, stream_length, mime)

    def on_decide_policy(self, web_view, decision, decision_type):
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
            logger.info('URI clicked:' + uri)
            decision.ignore()
            return True

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
        try:
            path = gfile.get_path()
            if not path:
                raise BookError('Empty path!')

            logger.info('Opening:' + path)

            doc = Epub(path)
        except BookError as e:
            raise
        else:
            if self.doc == doc:
                return

            if self.doc is not None:
                self.doc.disconnect(self.on_reload_chapter_id)

            self.doc = doc
            self.prepare_book()

    def prepare_book(self):
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
        self.reload_chapter()

        if self.on_reload_chapter_id is None:
            self.on_reload_chapter_id = self.doc.connect('notify::page',
                                                         self.reload_chapter)

        if self.on_load_set_pos_id is None:
            position = self.settings.get_position(self.identifier)
            self.on_load_set_pos_id = self.connect('load-changed',
                                                   self.on_load_set_pos,
                                                   position)

    def reload_chapter(self, epub=None, paramspec=None):
        """Use Epub's page number to retrieve the resource and load it into view.

        Args:
            epub (GObject.Object)
            paramspec (GObject.ParamSpec)
        """
        logger.info('Reloading:' + self.doc.get_current_path())

        bytes = self.doc.get_current_with_epub_uris()
        gbytes = GLib.Bytes(bytes)
        mime = self.doc.get_current_mime()
        encoding = 'UTF-8'
        base_uri = None

        self.load_bytes(gbytes, mime, encoding, base_uri)
        self.__page_turning = True

    def on_load_change(self, webview, load_event):
        """If the load event has finished, call setup_view()

        Args:
            webview (WebKit2.WebView)
            load_event (WebKit2.LoadEvent)
        """
        if load_event is WebKit2.LoadEvent.STARTED:
            logger.info('LoadEvent:STARTED')
        elif load_event is WebKit2.LoadEvent.COMMITTED:
            logger.info('LoadEvent:COMMITTED')
        elif load_event is WebKit2.LoadEvent.FINISHED:
            logger.info('LoadEvent:FINISHED')
            self.setup_view()
            self.__page_turning = False

            if not self.on_resize_id:
                self.on_resize_id = self.connect('size-allocate', self.on_resize)

    def setup_view(self):
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

        logger.info('Running view javascript...')
        self.run_javascript(bodyjs)
        self.run_javascript(wrapperjs)
        if self.settings.paginate:
            self.run_javascript(COL_JS)
        else:
            self.run_javascript(COL_JS_REMOVE)

    def on_load_set_pos(self, webview, load_event, position):
        """If the load event has finished, scroll to position

        Args:
            webview (WebKit2.WebView)
            load_event (WebKit2.LoadEvent)
        """
        if load_event is WebKit2.LoadEvent.FINISHED:
            logger.info('Setting position on load')
            self.set_scroll_position(position)
            self.disconnect(self.on_load_set_pos_id)
            self.on_load_set_pos_id = None

    def on_load_by_fragment(self, webview, load_event, fragment):
        """If the load event has finished, scroll to fragment

        Args:
            webview (WebKit2.WebView)
            load_event (WebKit2.LoadEvent)
            fragment (str)
        """
        if load_event is WebKit2.LoadEvent.FINISHED:
            self.set_scroll_to_fragment(fragment)
            self.disconnect(self.on_load_by_fragment_id)
            self.on_load_by_fragment_id = None

    def on_load_by_search(self, webview, load_event):
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
            self.on_load_by_search_id = None

    def on_resize(self, webview, gdk_rectangle):
        """Call position function on every size change

        Args:
            webview (WebKit2.WebView)
            gdk_rectangle (Gdk.Rectangle)
        """
        position = self.settings.get_position(self.identifier)
        self.set_scroll_position(position)

    def get_scroll_position(self):
        """Start DBUS call to obtain scroll position"""
        dbus_args = GLib.Variant("(ib)", (self.get_page_id(),
                                          self.settings.paginate))
        self.dbus_helper.call('GetScrollPosition',
                              dbus_args,
                              self.on_get_scroll_position,
                              self.get_page_id())

    def on_get_scroll_position(self, source, result):
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

    def set_scroll_position(self, position):
        """Start DBUS call to set scroll position

        Args:
            position (float)
        """
        dbus_args = GLib.Variant("(ibd)", (self.get_page_id(),
                                           self.settings.paginate,
                                           position))
        self.dbus_helper.call('SetScrollPosition',
                              dbus_args,
                              self.on_set_scroll_position,
                              self.get_page_id())

    def on_set_scroll_position(self, source, result):
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
                self.get_scroll_position()
            else:
                logger.warning('Could not set position:Unknown')

    def set_scroll_to_fragment(self, fragment):
        """Start DBUS call to set scroll position to an element id

        Args:
            fragment (str)
        """
        dbus_args = GLib.Variant("(ibs)", (self.get_page_id(),
                                           self.settings.paginate,
                                           fragment))
        self.dbus_helper.call('SetScrollToFragment',
                              dbus_args,
                              self.on_set_scroll_to_fragment,
                              self.get_page_id())

    def on_set_scroll_to_fragment(self, source, result):
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
                self.get_scroll_position()
            else:
                logger.warning('Could not set position to fragment:Unknown')

    def page_next(self):
        """Start DBUS call to change position to next page"""
        if not self.doc:
            return

        if (self.on_load_set_pos_id or
            self.on_load_by_fragment_id or
            self.on_load_by_search_id):
            return

        if self.__page_turning:
            return

        dbus_args = GLib.Variant("(ib)", (self.get_page_id(),
                                          self.settings.paginate))
        self.dbus_helper.call('ScrollNext',
                              dbus_args,
                              self.on_page_next,
                              self.get_page_id())

    def on_page_next(self, source, result):
        """Obtain result to page next position

        Args:
            source (GObject.Object)
            result (Gio.AsyncResult)
        """
        try:
            position_changed = source.call_finish(result)[0]
        except Exception as e:
            logger.error('Page Next:' + str(e))
        else:
            if position_changed:
                self.get_scroll_position()
            else:
                try:
                    self.chapter_next()
                except BookError as e:
                    pass
                else:
                    if self.on_load_set_pos_id is None:
                        position = 0.0
                        self.on_load_set_pos_id = self.connect('load-changed',
                                                             self.on_load_set_pos,
                                                             position)

    def page_prev(self):
        """Start DBUS call to change position to previous page"""
        if not self.doc:
            return

        if (self.on_load_set_pos_id or
            self.on_load_by_fragment_id or
            self.on_load_by_search_id):
            return

        if self.__page_turning:
            return

        dbus_args = GLib.Variant("(ib)", (self.get_page_id(),
                                          self.settings.paginate))
        self.dbus_helper.call('ScrollPrev',
                              dbus_args,
                              self.on_page_prev,
                              self.get_page_id())

    def on_page_prev(self, source, result):
        """Obtain result to page previous position

        Args:
            source (GObject.Object)
            result (Gio.AsyncResult)
        """
        try:
            position_changed = source.call_finish(result)[0]
        except Exception as e:
            logger.error('Page Previous:' + str(e))
        else:
            if position_changed:
                self.get_scroll_position()
            else:
                try:
                    self.chapter_prev()
                except BookError as e:
                    pass
                else:
                    if self.on_load_set_pos_id is None:
                        position = 100.0
                        self.on_load_set_pos_id = self.connect('load-changed',
                                                             self.on_load_set_pos,
                                                             position)

    def adjust_scroll_position(self):
        """Start DBUS call to adjust scroll position"""
        dbus_args = GLib.Variant("(ib)", (self.get_page_id(),
                                          self.settings.paginate))
        self.dbus_helper.call('AdjustScrollPosition',
                              dbus_args,
                              self.on_adjust_scroll_position,
                              self.get_page_id())

    def on_adjust_scroll_position(self, source, result):
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
                self.get_scroll_position()

    def get_chapter(self):
        """Returns an int as chapter"""
        if self.doc:
            return self.doc.get_page()
        else:
            return None

    def set_chapter(self, chapter):
        """Set current chapter

        Args:
            chapter (int)
        """
        if self.doc:
            self.doc.set_page(chapter)

    def chapter_next(self):
        if self.doc:
            try:
                self.doc.go_next()
            except BookError as e:
                raise e

    def chapter_prev(self):
        if self.doc:
            try:
                self.doc.go_prev()
            except BookError as e:
                raise e

    def get_current_path(self):
        if self.doc:
            return self.doc.get_current_path()
        else:
            return None

    def refresh_view(self):
        """Start the restyling of current chapter"""
        if self.doc:
            self.setup_view()
            position = self.settings.get_position(self.identifier)
            self.set_scroll_position(position)

    def get_title(self):
        if self.doc:
            return self.doc.title
        else:
            return None

    def get_author(self):
        if self.doc:
            creator_list = self.doc.get_metadata('creator')
            if creator_list:
                return creator_list[0]
        else:
            return None

    def get_path(self):
        if self.doc:
            return self.doc.path
        else:
            return None

    def find_text(self, search_text):
        """Start search in webview and document. Connect search signals.

        Args:
            search_text (str)
        """
        if not self.doc:
            return

        if search_text:
            web_find_controller = self.get_find_controller()
            if self.on_text_found_id is None:
                self.on_text_found_id = web_find_controller.connect('found-text',
                                                                    self.on_found_text)
            if self.on_text_not_found_id is None:
                self.on_text_not_found_id = web_find_controller.connect('failed-to-find-text',
                                                                        self.on_text_not_found)
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
            self.on_text_found_id = None
        if self.on_text_not_found_id:
            web_find_controller.disconnect(self.on_text_not_found_id)
            self.on_text_not_found_id = None
        self.__matches_list = None

    def find_next(self):
        if not self.doc:
            return

        if not self.__matches_list:
            return

        web_find_controller = self.get_find_controller()
        web_find_controller.search_next()
        self.__is_match_prev = False
        self.adjust_scroll_position()

    def find_prev(self):
        if not self.doc:
            return

        if not self.__matches_list:
            return

        web_find_controller = self.get_find_controller()
        web_find_controller.search_previous()
        self.__is_match_prev = True
        self.adjust_scroll_position()

    def on_found_text(self, web_find_controller, match_count):
        """Fix position because web_find_controller centers the match.

        Args:
            web_find_controller (WebKit2.FindController)
            match_count (int)
        """
        self.get_scroll_position()

    def on_text_not_found(self, web_find_controller):
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
            if self.on_load_by_search_id is None:
                if self.__is_match_prev and self.on_load_set_pos_id is None:
                    position = 100.0
                    self.on_load_set_pos_id = self.connect('load-changed',
                                                           self.on_load_set_pos,
                                                           position)
                self.on_load_by_search_id = self.connect('load-changed',
                                                         self.on_load_by_search)
        else:
            logger.info('No coincidences in epub')
