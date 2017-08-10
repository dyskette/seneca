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

from .settings import Settings

import logging
logging.basicConfig(level=logging.WARNING)

import gi
gi.require_version('WebKit2', '4.0')
gi.require_version('Gepub', '0.5')
from gi.repository import Gio, WebKit2, Gepub

class Book(WebKit2.WebView):

    def __init__(self, _gfile):
        WebKit2.WebView.__init__(self)

        self.__doc = None

        # Used internally
        self.__view_width = 0
        self.__scroll_width = 0
        self.__chapter_pos = 0
        self.__is_page_prev = False

        # User settings
        self.__set = Settings()

        context = self.get_context()
        context.register_uri_scheme('epub', self.on_epub_scheme)
        settings = self.get_settings()
        settings.set_property('enable-smooth-scrolling', True)
        self.connect('load-changed', self.on_load_change)
        self.connect('size-allocate', self.on_size_change)

        try:
            _path = _gfile.get_path()
            if not _path:
                raise AttributeError('GFile has empty path')
            gepubdoc = Gepub.Doc.new(_path)
        except Exception as e:
            raise AttributeError(e)
        else:
            self.set_doc(gepubdoc)

    def get_doc(self):
        return self.__doc

    def set_doc(self, gepubdoc):
        """ Receives a Gepub.Doc object. Disconnects a reload signal if there was a
        previous object, and connects the new object signal.

        Parameters:
            Gepub.Doc - An epub document object.
        """
        if self.__doc == gepubdoc:
            return

        if self.__doc is not None:
            self.__doc.disconnect_by_func(self.reload_current_chapter)

        self.__doc = gepubdoc

        if self.__doc:
            self.reload_current_chapter()
            # See: GObject.Object.signals.notify
            self.__doc.connect('notify::page', self.reload_current_chapter)

    def reload_current_chapter(self, gepubdoc=None, event=None):
        """ Reload current Gepub.Doc chapter in WebView. This function is
        connected to every page switch.
        """
        self.__scroll_width = 0
        self.__view_width = 0
        self.__chapter_pos = 0

        _bytes = self.__doc.get_current_with_epub_uris()
        _mime = self.__doc.get_current_mime()
        _encoding = 'UTF-8'
        _base_uri = None

        logging.info('Reloading: epub:///{0}'.format(self.__doc.get_current_path()))
        self.load_bytes(_bytes, _mime, _encoding, _base_uri)

    def on_epub_scheme(self, request):
        """ Callback function. Everytime something is requested, like a css or
        image path. It uses the WebKit2.URISchemeRequest to find out the path
        requested and get it from the Gepub.Doc object.

        Finish a WebKit2.URISchemeRequest by setting the contents of the request
        and its mime type.

        Parameters:
            request (WebKit2.URISchemeRequest)
        """
        if not self.__doc:
            return

        _uri = request.get_uri()
        _path = _uri[8:]
        _bytes = self.__doc.get_resource(_path)

        stream = Gio.MemoryInputStream.new_from_bytes(_bytes)
        stream_length = _bytes.get_size()
        mime = self.__doc.get_resource_mime(_path)

        logging.info('Delivering: {0}'.format(_uri))
        request.finish(stream, stream_length, mime)

    def on_load_change(self, webview, load_event):
        if load_event is WebKit2.LoadEvent.FINISHED:
            logging.info('Load finished: Running javascript')
            self.setup_view()

    def on_size_change(self, webview, gdk_rectangle):
        logging.info('Size changed: Running javascript')
        self.setup_view()

    def setup_view(self):
        """ Sets up the WebView and all variables for pagination if it's active.
        This function is called at every size, page or settings change.

        - Obtains the width of the view.
        - Adds a child to <body> with margin (left and right) style when necessary
        - Adds font and lineheight styles to child of <body> when necessary
        - If pagination is active:
            - Set column and overflow styles, also margin (top and bottom)
            - Setup position if we are coming from a page_prev call
            - If position is non zero, we call position adjustment function

        """
        self.__view_width = self.get_allocation().width
        logging.info('View width: {0}'.format(self.__view_width))

        js_string = '''
        if (!document.querySelector('#bookywrapper'))
            document.body.innerHTML = '<div id="bookywrapper">' + document.body.innerHTML + '</div>';

        document.querySelector('#bookywrapper').style.marginLeft = '{margin}px';
        document.querySelector('#bookywrapper').style.marginRight = '{margin}px';
        '''.format(margin=self.__set.margin)
        self.run_javascript(js_string)

        if self.__set.fontfamily:
            js_string = 'document.querySelector(\'#bookywrapper\').style.fontFamily = \'{0}\';'.format(
                        self.__set.fontfamily)
            self.run_javascript(js_string)
        if self.__set.fontweight:
            js_string = 'document.querySelector(\'#bookywrapper\').style.fontWeight = \'{0}\';'.format(
                        self.__set.fontweight)
            self.run_javascript(js_string)
        if self.__set.fontstyle:
            js_string = 'document.querySelector(\'#bookywrapper\').style.fontStyle = \'{0}\';'.format(
                        self.__set.fontstyle)
            self.run_javascript(js_string)
        if self.__set.fontstretch:
            js_string = 'document.querySelector(\'#bookywrapper\').style.fontStretch = \'{0}\';'.format(
                        self.__set.fontstretch)
            self.run_javascript(js_string)
        if self.__set.fontsize:
            js_string = 'document.querySelector(\'#bookywrapper\').style.fontSize = \'{0}px\';'.format(
                        self.__set.fontsize)
            self.run_javascript(js_string)
        if self.__set.lineheight:
            js_string = 'document.querySelector(\'#bookywrapper\').style.lineHeight = \'{0}\';'.format(
                        self.__set.lineheight)
            self.run_javascript(js_string)

        if self.__set.paginate:
            # Pagination: We create one column and hide the overflow.
            js_string = '''
            document.body.style.overflow = 'hidden';
            document.body.style.margin = '20px 0px 20px 0px';
            document.body.style.padding = '0px';
            document.body.style.columnWidth = window.innerWidth+'px';
            document.body.style.height = (window.innerHeight - 40) +'px';
            document.body.style.columnGap = '0px';
            '''
            self.run_javascript(js_string)

            js_string = 'document.title = document.body.scrollWidth;'
            self.run_javascript(js_string, None, self.get_width_from_title, None)

    def get_width_from_title(self, webview, result, user_data):
        try:
            js_result = self.run_javascript_finish(result)
        except Exception as e:
            raise ValueError('Error getting the scroll width: {0}'.format(e))

        self.__scroll_width = int(self.get_title())
        logging.info('Vertical scroll length: {0}'.format(self.__scroll_width))

        # When doing a page_prev, don't jump to the beginning of the chapter,
        # instead show the end of the chapter. But only if it's long enough.
        if self.__is_page_prev:
            logging.info('Page prev: Set chapter position accordingly')
            self.__chapter_pos = 100 * self.__scroll_width // 100
            if self.__chapter_pos > (self.__scroll_width - self.__view_width):
                self.__chapter_pos = self.__scroll_width - self.__view_width
            self.__is_page_prev = False

        if self.__chapter_pos:
            self.adjust_chapter_pos()


    def adjust_chapter_pos(self):
        """ Position adjustment function.

        When the view is paginated, adjust chapter position given an arbitrary
        number, i.e. go to the next page if the position given is closer to it.
        """
        _page = self.__chapter_pos // self.__view_width
        _next = _page + 1

        _page_pos = self.__view_width * _page
        _next_pos = self.__view_width * _next

        _d1 = self.__chapter_pos - _page_pos
        _d2 = _next_pos - self.__chapter_pos

        # The less, the better...
        if _d1 < _d2:
            self.__chapter_pos = _page_pos
        else:
            self.__chapter_pos = _next_pos

        # Alright, we are good to go.
        self.scroll_to_position()

    def scroll_to_position(self):
        logging.info('Scrolling to... {0}'.format(self.__chapter_pos))
        js_string = 'document.querySelector(\'body\').scrollTo({0}, 0)'.format(self.__chapter_pos)
        self.run_javascript(js_string)

    def get_paginate(self):
        return self.__set.paginate

    def set_paginate(self, b):
        self.__set.paginate = b
        self.__set.save()
        self.reload_current_chapter()

    def page_next(self):
        self.__chapter_pos = self.__chapter_pos + self.__view_width
        if self.__chapter_pos > (self.__scroll_width - self.__view_width):
            self.__doc.go_next()

        self.scroll_to_position()

    def page_prev(self):
        if self.__chapter_pos == 0 and self.get_chapter() == 0:
            return

        self.__chapter_pos = self.__chapter_pos - self.__view_width
        if self.__chapter_pos < 0:
            self.__is_page_prev = True
            self.__doc.go_prev()

        self.scroll_to_position()

    def get_position(self):
        if not self.__chapter_pos:
            return 0

        return self.__chapter_pos / self.__scroll_width * 100

    def set_position(self, p):
        self.__chapter_pos = p * self.__scroll_width / 100
        self.adjust_chapter_pos()

    def get_chapter_length(self):
        return self.__scroll_width

    def get_chapter(self):
        return self.__doc.get_page()

    def set_chapter(self, c):
        self.__doc.set_page(c)

    def chapter_next(self):
        self.__doc.go_next()

    def chapter_prev(self):
        self.__doc.go_prev()

    def get_margin(self):
        return self.__set.margin

    def set_margin(self, m):
        self.__set.margin = m
        self.__set.save()
        self.setup_view()

    def get_color(self):
        return self.__set.color

    def set_color(self, c):
        self.__set.color = c
        self.__set.save()
        self.setup_view()

    def get_font(self):
        return [self.__set.fontfamily,
                self.__set.fontweight,
                self.__set.fontstyle,
                self.__set.fontstretch,
                self.__set.fontsize]

    def set_font(self, f):
        self.__set.fontfamily = f[0]
        self.__set.fontweight = f[1]
        self.__set.fontstyle = f[2]
        self.__set.fontstretch = f[3]
        self.__set.fontsize = f[4]
        self.__set.save()
        self.setup_view()

    def get_fontsize(self):
        return self.__set.fontsize

    def set_fontsize(self, f):
        self.__set.fontsize = f
        self.__set.save()
        self.setup_view()

    def get_lineheight(self):
        return self.__set.lineheight

    def set_lineheight(self, l):
        self.__set.lineheight = l
        self.__set.save()
        self.setup_view()

    def get_title(self):
        return self.__doc.get_metadata('title')

    def get_author(self):
        return self.__doc.get_metadata('creator')
