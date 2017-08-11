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
logging.basicConfig(level=logging.WARNING)

import gi
gi.require_version('Gdk', '3.0')
gi.require_version('WebKit2', '4.0')
gi.require_version('Gepub', '0.5')
from gi.repository import Gdk, Gio, WebKit2, Gepub

class Book(WebKit2.WebView):

    def __init__(self, _settings):
        WebKit2.WebView.__init__(self)

        self.__doc = None
        self.__view_width = 0
        self.__scroll_width = 0
        self.__chapter_pos = 0
        self.__is_page_prev = False
        self.__chapters = []
        self.__settings = _settings

        self.__wk_settings = self.get_settings()
        self.__wk_context = self.get_context()

        _gdk_color = Gdk.Color.parse(self.__settings.color_bg)
        _gdk_rgba = Gdk.RGBA.from_color(_gdk_color[1])
        self.set_background_color(_gdk_rgba)
        self.__wk_settings.set_property('default-font-size', self.__settings.fontsize)

        self.__wk_context.register_uri_scheme('epub', self.on_epub_scheme)
        self.connect('load-changed', self.on_load_change)
        self.connect('size-allocate', self.on_size_change)

    def get_doc(self):
        return self.__doc

    def set_doc(self, _gfile):
        """ Receives a GFile object. Disconnects a reload signal if there was a
        previous object, and connects the new object signal.

        Parameters:
            GFile
        """
        try:
            _path = _gfile.get_path()
            if not _path:
                raise AttributeError('GFile has empty path')

            _gepubdoc = Gepub.Doc.new(_path)
        except Exception as e:
            raise AttributeError(e)
        else:
            if self.__doc == _gepubdoc:
                return

            if self.__doc is not None:
                self.__doc.disconnect_by_func(self.reload_current_chapter)

            self.__doc = _gepubdoc

            for i in range(self.__doc.get_n_pages()):
                self.__chapters.append(self.__doc.get_current_path())
                self.__doc.go_next()
            self.__doc.set_page(0)

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
        """ Callback function. Everytime something is requested. It uses the
        WebKit2.URISchemeRequest to find out the path requested and get it from
        the Gepub.Doc object.

        Finish a WebKit2.URISchemeRequest by setting the contents of the request
        and its mime type.

        Parameters:
            request (WebKit2.URISchemeRequest)
        """
        if not self.__doc:
            return

        _uri = request.get_uri()
        _path = _uri[8:]

        if _path == self.__doc.get_current_path():
            return

        # Maybe is epub:///link/file#id
        _hash = _path.find('#')
        if _hash != -1:
            _id = _path[_hash:]
            _path = _path[:_hash]

            if _path == self.__doc.get_current_path():
                logging.info('Scrolling in same chapter to... {0}'.format(_id))
                js_string = 'window.location = \'{0}\';'.format(_id)
                self.run_javascript(js_string)
                return

        for i in range(len(self.__chapters)):
            if _path in self.__chapters[i]:
                self.__doc.set_page(i)
                if _hash != -1:
                    self.connect('load-changed', self.on_scroll_to_id, _id)
                return

        _bytes = self.__doc.get_resource(_path)

        stream = Gio.MemoryInputStream.new_from_bytes(_bytes)
        stream_length = _bytes.get_size()
        mime = self.__doc.get_resource_mime(_path)

        logging.info('Delivering: {0}'.format(_uri))
        request.finish(stream, stream_length, mime)

    def on_load_change(self, webview, load_event):
        if load_event is WebKit2.LoadEvent.FINISHED:
            logging.info('Load event finished')
            self.setup_view()

    def on_size_change(self, webview, gdk_rectangle):
        logging.info('Size changed')
        self.recalculate_content()

    def setup_view(self):
        """ Sets up the WebView content. It adds styles to the body itself and
        to a child element of body.

        This function is called at every page switch or settings change.
        """
        _gdk_color = Gdk.Color.parse(self.__settings.color_bg)
        _gdk_rgba = Gdk.RGBA.from_color(_gdk_color[1])
        self.set_background_color(_gdk_rgba)
        self.__wk_settings.set_property('default-font-size', self.__settings.fontsize)

        body_js = '''
        document.body.style.backgroundColor = '{bg}';
        document.body.style.color = '{fg}';
        document.body.style.margin = '0px';
        '''.format(bg=self.__settings.color_bg,
                   fg=self.__settings.color_fg)

        wrapper_js = '''
        if (!document.getElementById('bookBodyInnerWrapper'))
            document.body.innerHTML = '<div id="bookBodyInnerWrapper">' + document.body.innerHTML + '</div>';

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
        '''.format(mg=self.__settings.margin,
                   bg=self.__settings.color_bg,
                   fg=self.__settings.color_fg,
                   fs0=self.__settings.fontfamily,
                   fs1=self.__settings.fontweight,
                   fs2=self.__settings.fontstyle,
                   fs3=self.__settings.fontstretch,
                   fs4=self.__settings.fontsize,
                   lh=self.__settings.lineheight)

        column_js_inner = '''
        function resizeColumn() {
            document.body.style.columnWidth = window.innerWidth + 'px';
            document.body.style.height = (window.innerHeight - 40) +'px';
        }
        resizeColumn();
        window.addEventListener('resize', resizeColumn);
        '''

        column_js = '''
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
        '''.format(column_js_inner)

        img_js_inner = '''
        function resizeImages() {
            var avail_width = window.innerWidth - 40;
            var avail_height = window.innerHeight - 40;

            var img = document.getElementsByTagName('img');
            var len = img.length;

            for (var i = 0; i < len; i++) {
                var image_width  = img[i].naturalWidth;
                var image_height = img[i].naturalHeight;
                var image_ratio = image_width / image_height;
                var avail_ratio = avail_width / avail_height;
                var width;
                var height;

                if (image_width >= avail_width || image_height >= avail_height) {
                    if (avail_ratio > image_ratio) {
                        width = Math.floor(image_width * avail_height / image_height);
                        height = avail_height;
                    } else {
                        width = avail_width;
                        height = Math.floor(image_height * avail_width / image_width);
                    }
                } else {
                    width = image_width;
                    height = image_height;
                }

                console.log('Image ' + i + ': ' + width + ' x ' + height);
                img[i].style.width = width + 'px';
                img[i].style.height = height + 'px';
            }
        }

        resizeImages();
        window.addEventListener('resize', resizeImages);
        '''

        img_js = '''
        if (!document.getElementById('imgJS')) {{
            var child_script = document.createElement('script');
            child_script.type = 'text/javascript';
            child_script.id = 'imgJS'
            child_script.innerHTML = `{0}`;
            document.body.appendChild(child_script);
        }}
        '''.format(img_js_inner)

        logging.info('Running body and wrapper javascript...')
        self.run_javascript(body_js)
        self.run_javascript(wrapper_js)
        if self.__settings.paginate:
            logging.info('Running pagination javascript...')
            self.run_javascript(column_js)
            # FIXME: This break some books, I was trying to imitate calibre viewer.
            #self.run_javascript(img_js)

        self.recalculate_content()

    def recalculate_content(self):
        self.__view_width = self.get_allocation().width
        logging.info('View width: {0}'.format(self.__view_width))

        if self.__settings.paginate:
            js_string = 'document.title = document.body.scrollWidth;'
            self.run_javascript(js_string, None, self.get_width_from_title, None)

    def get_width_from_title(self, webview, result, user_data):
        try:
            js_result = self.run_javascript_finish(result)
        except Exception as e:
            logging.error('Error getting scroll width: {0}'.format(e))

        self.__scroll_width = int(self.get_property('title'))
        logging.info('Scroll width: {0}'.format(self.__scroll_width))

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

    def get_id_position_from_title(self, webview, result, user_data):
        try:
            js_result = self.run_javascript_finish(result)
        except Exception as e:
            logging.error('Error getting id position: {0}'.format(e))

        self.__chapter_pos = int(self.get_property('title'))
        logging.info('Id position: {0}'.format(self.__chapter_pos))
        self.adjust_chapter_pos()

    def adjust_chapter_pos(self):
        """ Position adjustment function.

        When the view is paginated, adjust chapter position given an arbitrary
        number, i.e. go to the next page if the position given is closer to it.
        """
        logging.info('Adjusting position value')
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
        logging.info('Scrolling to... {0}'.format(self.get_position()))
        js_string = 'document.querySelector(\'body\').scrollTo({0}, 0)'.format(self.__chapter_pos)
        self.run_javascript(js_string)

    def on_scroll_to_id(self, webview, load_event, _id):
        # TODO: Test scrolling when paginated is True
        if load_event is WebKit2.LoadEvent.FINISHED:
            logging.info('Scrolling in new chapter to... {0}'.format(_id))
            js_string = 'window.location = \'{0}\';'.format(_id)
            self.run_javascript(js_string)
        self.disconnect_by_func(self.on_scroll_to_id)

    def get_paginate(self):
        return self.__settings.paginate

    def set_paginate(self, b):
        self.__settings.paginate = b
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

    def set_settings(self, _settings):
        self.__settings = _settings
        self.setup_view()

    def get_title(self):
        return self.__doc.get_metadata('title')

    def get_author(self):
        return self.__doc.get_metadata('creator')
