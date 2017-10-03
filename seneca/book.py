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
if (!document.getElementById('bookBodyInnerWrapper'))
    document.body.innerHTML = '<div id="bookBodyInnerWrapper">' +
                              document.body.innerHTML +
                              '</div>';

var wrapper = document.getElementById('bookBodyInnerWrapper');

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
document.body.style.overflow = 'hidden';
document.body.style.margin = '20px 0px 20px 0px';
document.body.style.columnGap = '0px';
'''.format(COL_JS_INNER)

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

    def __init__(self, _settings):
        self.__wk_context = WebKit2.WebContext.get_default()

        # WebExtensions
        application = Gio.Application.get_default()
        variant_lvl = GLib.Variant.new_int32(logger.getEffectiveLevel())
        self.__wk_context.set_web_extensions_directory(application.extensiondir)
        self.__wk_context.set_web_extensions_initialization_user_data(variant_lvl)

        # Document viewer cache model
        self.__wk_context.set_cache_model(WebKit2.CacheModel.DOCUMENT_VIEWER)
        WebKit2.WebView.__init__(self, web_context=self.__wk_context)

        self.__doc = None
        self.__identifier = None
        self.__view_width = 0
        self.__scroll_width = 0
        self.__chapter_pos = 0
        self.__is_page_prev = False
        self.__settings = _settings
        self.__helper = DBusHelper()

        self.__wk_settings = self.get_settings()
        self.__wk_find_controller = self.get_find_controller()

        # Background color of webview
        gdk_color = Gdk.Color.parse(self.__settings.color_bg)
        gdk_rgba = Gdk.RGBA.from_color(gdk_color[1])
        self.set_background_color(gdk_rgba)

        # Font size of webview
        self.__wk_settings.set_property('default-font-size', self.__settings.fontsize)
        if logger.getEffectiveLevel() <= logging.INFO:
            self.__wk_settings.set_property('enable-developer-extras',
                                            True)

        # Connecting functions
        self.__wk_context.register_uri_scheme('epub', self.on_epub_scheme)
        self.__wk_context.connect('initialize-web-extensions', self.on_initialize_web_extensions)
        self.__wk_find_controller.connect('found-text', self.on_found_text)
        self.connect('load-changed', self.on_load_change)
        self.connect('size-allocate', self.on_size_change)

    def get_doc(self):
        return self.__doc

    def set_doc(self, gfile):
        """ Receives a GFile object and uses Gepub.Doc to parse it.

        Parameters:
            GFile
        """
        try:
            path = gfile.get_path()
            if not path:
                raise BookError('Empty path!')

            doc = Epub(path)
        except BookError as e:
            raise
        else:
            if self.__doc == doc:
                return

            if self.__doc is not None:
                self.__doc.disconnect_by_func(self.reload_current_chapter)

            logger.info('Opening {0}'.format(path))
            self.__doc = doc
            self.prepare_book()

    def prepare_book(self):
        """ Refreshing relevant variables for the book.
        """
        logger.info('Preparing book with settings')
        # Identifier in settings
        if self.__doc.identifier:
            self.__identifier = self.__doc.identifier
        else:
            self.__identifier = self.get_author() + self.get_title()

        # Add book to settings
        if not self.__settings.get_book(self.__identifier):
            self.__settings.add_book(self.__identifier)

        # Position
        chapter = self.__settings.get_chapter(self.__identifier)
        position = self.__settings.get_position(self.__identifier)

        self.set_chapter(chapter)
        self.reload_current_chapter()
        self.__chapter_pos = position

        # Signal: GObject.Object.signals.notify
        self.__doc.connect('notify::page', self.reload_current_chapter)

    def reload_current_chapter(self, unused_a=None, unused_b=None):
        """ Reload current chapter in WebView. This function is
        connected to every page switch.
        """
        logger.info('Reloading: {0}'.format(self.get_current_path()))
        self.__scroll_width = 0
        self.__chapter_pos = 0

        gbytes = self.__doc.get_current_with_epub_uris()
        mime = self.__doc.get_current_mime()
        encoding = 'UTF-8'
        base_uri = None

        self.load_bytes(gbytes,
                        mime,
                        encoding,
                        base_uri)

        self.__settings.save_pos(self.__identifier,
                                 self.get_chapter(),
                                 self.__chapter_pos)

    def on_epub_scheme(self, request):
        """ Callback function. Everytime something is requested. It uses the
        WebKit2.URISchemeRequest to find out the path and get it.

        Finish a WebKit2.URISchemeRequest by setting the contents of the request
        and its mime type.

        Parameters:
            request (WebKit2.URISchemeRequest)
        """
        logger.info('Resolving epub scheme')
        if not self.__doc:
            return

        uri = request.get_uri()
        logger.info('Resource request: {}'.format(uri))

        try:
            path, fragment = self._get_path_fragment(uri)
            if self.jump_to_path_fragment(path, fragment):
                return
        except BookError as e:
            logger.error('Could not get resource: {}'.format(e))
            request.finish_error(GLib.Error(str(e)))
            return

        gbytes = self.__doc.get_resource(path)
        stream = Gio.MemoryInputStream.new_from_bytes(gbytes)
        stream_length = gbytes.get_size()
        mime = self.__doc.get_resource_mime(path)

        request.finish(stream, stream_length, mime)

    def _get_path_fragment(self, _path):
        path = ''
        fragment = ''

        if _path:
            soup_uri = Soup.URI.new(_path)
            path = soup_uri.get_path()[1:]
            fragment = soup_uri.get_fragment() or ''

        return [path, fragment]

    def jump_to_path_fragment(self, path, fragment):
        if not path:
            path = self.get_current_path()

        if not self.__doc.is_navigation_type(path):
            return False

        current = self.get_current_path()
        if path == current:
            logger.info('Same chapter')
            if fragment:
                self.set_scroll_to_fragment(fragment)
            else:
                self.set_position(0)
            return True
        else:
            logger.info('Changing chapter')
            self.__doc.set_page_by_path(path)
            if fragment:
                self.connect('load-changed', self.on_jump_to_path_fragment, fragment)
            return True

    def on_jump_to_path_fragment(self, webview, load_event, fragment):
        if load_event is WebKit2.LoadEvent.FINISHED:
            self.set_scroll_to_fragment(fragment)

    def on_load_change(self, webview, load_event):
        if load_event is WebKit2.LoadEvent.FINISHED:
            logger.info('Load event finished')
            self.setup_view()

    def setup_view(self):
        """ Sets up the WebView content. It adds styles to the body itself and
        to a child element of body.

        This function is called at every page switch or settings change.
        """
        gdk_color = Gdk.Color.parse(self.__settings.color_bg)
        gdk_rgba = Gdk.RGBA.from_color(gdk_color[1])
        self.set_background_color(gdk_rgba)
        self.__wk_settings.set_property('default-font-size', self.__settings.fontsize)

        bodyjs = BODY_JS.format(bg=self.__settings.color_bg,
                                 fg=self.__settings.color_fg)

        wrapperjs = WRAPPER_JS.format(mg=self.__settings.margin,
                                       bg=self.__settings.color_bg,
                                       fg=self.__settings.color_fg,
                                       fs0=self.__settings.fontfamily,
                                       fs1=self.__settings.fontweight,
                                       fs2=self.__settings.fontstyle,
                                       fs3=self.__settings.fontstretch,
                                       fs4=self.__settings.fontsize,
                                       lh=self.__settings.lineheight)

        logger.info('Running view javascript...')
        self.run_javascript(bodyjs)
        self.run_javascript(wrapperjs)
        if self.__settings.paginate:
            self.run_javascript(COL_JS)

        self.recalculate_content()

    def on_size_change(self, webview, gdk_rectangle):
        logger.info('Size changed')
        self.recalculate_content()

    def recalculate_content(self):
        self.__view_width = self.get_allocation().width
        logger.info('View width: {0}'.format(self.__view_width))

        if self.__settings.paginate:
            dbus_args = GLib.Variant("(ib)", (self.get_page_id(),
                                              self.__settings.paginate))
            self.__helper.call('GetScrollLength',
                               dbus_args,
                               self.on_recalculate_content,
                               self.get_page_id())

    def on_recalculate_content(self, source, result):
        """Obtain document length

        Args:
            source (GObject.Object)
            result (Gio.AsyncResult)
        """
        try:
            self.__scroll_width = source.call_finish(result)[0]
            logger.info('Scroll width: {0}'.format(self.__scroll_width))
        except Exception as e:
            logger.error('on_get_width: {}'.format(e))


        # When doing a page_prev, don't jump to the beginning of the chapter,
        # instead show the end of the chapter. But only if it's long enough.
        if self.__is_page_prev:
            logger.info('Page prev: Set chapter position accordingly')
            if self.__scroll_width > self.__view_width:
                self.__chapter_pos = self.__scroll_width - self.__view_width
            else:
                self.__chapter_pos = 0
            self.__is_page_prev = False

        if self.__chapter_pos:
            self.adjust_chapter_pos()

    def get_scroll_position(self):
        dbus_args = GLib.Variant("(ib)", (self.get_page_id(),
                                          self.__settings.paginate))
        self.__helper.call('GetScrollPosition',
                           dbus_args,
                           self.on_get_scroll_position,
                           self.get_page_id())

    def on_get_scroll_position(self, source, result):
        """Obtain scroll position and call adjust function

        Args:
            source (GObject.Object)
            result (Gio.AsyncResult)
        """
        try:
            position = source.call_finish(result)[0]
            logger.info('Scroll position: {0}'.format(position))
        except Exception as e:
            logger.error('on_get_scroll_position: {}'.format(e))

        if position != self.__chapter_pos:
            self.__chapter_pos = position
            self.adjust_chapter_pos()

    def adjust_chapter_pos(self):
        """ Position adjustment function.

        When the view is paginated, adjust chapter position given an arbitrary
        number, i.e. go to the next page if the position given is closer to it.
        """
        logger.info('Adjusting position value')
        page = self.__chapter_pos // self.__view_width
        next = page + 1

        page_pos = self.__view_width * page
        next_pos = self.__view_width * next

        d1 = self.__chapter_pos - page_pos
        d2 = next_pos - self.__chapter_pos

        # The less, the better...
        if d1 < d2:
            self.__chapter_pos = page_pos
        else:
            self.__chapter_pos = next_pos

        # Alright, we are good to go.
        self.set_scroll_position(self.__chapter_pos)

    def set_scroll_position(self, position):
        dbus_args = GLib.Variant("(ibi)", (self.get_page_id(),
                                           self.__settings.paginate,
                                           position))
        self.__helper.call('SetScrollPosition',
                           dbus_args,
                           self.on_set_scroll_position,
                           self.get_page_id())

    def on_set_scroll_position(self, source, result):
        """Obtain and save scroll position

        Args:
            source (GObject.Object)
            result (Gio.AsyncResult)
        """
        try:
            self.__chapter_pos = source.call_finish(result)[0]
            logger.info('Scroll position: {0}'.format(self.__chapter_pos))
            self.__settings.save_pos(self.__identifier,
                                     self.get_chapter(),
                                     self.__chapter_pos)
        except Exception as e:
            logger.error('on_pagination_scrollto: {}'.format(e))

    def set_scroll_to_fragment(self, fragment):
        dbus_args = GLib.Variant("(ibs)", (self.get_page_id(),
                                           self.__settings.paginate,
                                           fragment))
        self.__helper.call('SetScrollToId',
                           dbus_args,
                           self.on_set_scroll_to_fragment,
                           self.get_page_id())

    def on_set_scroll_to_fragment(self, source, result):
        """Obtain fragment position

        Args:
            source (GObject.Object)
            result (Gio.AsyncResult)
        """
        try:
            position = source.call_finish(result)[0]
            logger.info('Fragment position: {0}'.format(position))
        except Exception as e:
            logger.error('on_set_scroll_to_fragment: {}'.format(e))

        if position != self.__chapter_pos:
            self.__chapter_pos = position
            self.adjust_chapter_pos()

    def get_paginate(self):
        return self.__settings.paginate

    def set_paginate(self, b):
        self.__settings.paginate = b
        self.reload_current_chapter()

    def page_next(self):
        self.__chapter_pos = self.__chapter_pos + self.__view_width

        _smaller_than_view =  (self.__scroll_width - self.__chapter_pos) < self.__view_width

        if _smaller_than_view and self.__view_width > 800:
            _limit = self.__scroll_width - int(self.__view_width / 2)
        else:
            _limit = self.__scroll_width - self.__view_width

        if self.__chapter_pos > _limit:
            self.__doc.go_next()
        else:
            self.set_scroll_position(self.__chapter_pos)

    def page_prev(self):
        if self.__chapter_pos == 0 and self.get_chapter() == 0:
            return

        if self.__is_page_prev:
            return

        self.__chapter_pos = self.__chapter_pos - self.__view_width

        if self.__chapter_pos < 0:
            self.__is_page_prev = True
            self.__doc.go_prev()
        else:
            self.set_scroll_position(self.__chapter_pos)

    def get_position(self):
        if not self.__chapter_pos:
            return 0

        return self.__chapter_pos / self.__scroll_width * 100

    def set_position(self, p):
        self.__chapter_pos = int(p * self.__scroll_width / 100)
        self.adjust_chapter_pos()

    def get_chapter_length(self):
        return self.__scroll_width

    def get_current_path(self):
        return self.__doc.get_current_path()

    def get_chapter(self):
        return self.__doc.get_page()

    def set_chapter(self, c):
        self.__doc.set_page(c)

    def chapter_next(self):
        self.__doc.go_next()

    def chapter_prev(self):
        self.__doc.go_prev()

    def set_settings(self, _settings):
        self.__settings = _settings
        self.setup_view()

    def get_title(self):
        return self.__doc.title

    def get_author(self):
        creator_list = self.__doc.get_metadata('creator')
        if creator_list:
            return creator_list[0]

    def get_path(self):
        return self.__doc.path

    def find_text(self, search_text):
        max_match_count = 1000
        self.__wk_find_controller.search(search_text,
                                         WebKit2.FindOptions.CASE_INSENSITIVE,
                                         max_match_count)


    def find_next(self):
        self.__wk_find_controller.search_next()

    def find_prev(self):
        self.__wk_find_controller.search_previous()

    def on_found_text(self, find_controller, match_count):
        self.get_scroll_position()

