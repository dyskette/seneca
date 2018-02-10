# pagination.py
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
from gi.repository import Gio, GLib

logger = logging.getLogger(name='webextensions.pagination')
SENECA_INNER_WRAPPER = '<div id="SenecaInnerWrapper">\n{}\n</div>'


class Server:

    def __init__(self, con, path):
        method_outargs = {}
        method_inargs = {}
        for interface in Gio.DBusNodeInfo.new_for_xml(self.__doc__).interfaces:

            for method in interface.methods:
                method_outargs[method.name] = '(' + ''.join([arg.signature for arg in method.out_args]) + ')'
                method_inargs[method.name] = tuple(arg.signature for arg in method.in_args)

            con.register_object(object_path=path,
                                interface_info=interface,
                                method_call_closure=self.on_method_call)

        self.method_inargs = method_inargs
        self.method_outargs = method_outargs

    def on_method_call(self,
                       connection,
                       sender,
                       object_path,
                       interface_name,
                       method_name,
                       parameters,
                       invocation):

        args = list(parameters.unpack())
        for i, sig in enumerate(self.method_inargs[method_name]):
            if sig is 'h':
                msg = invocation.get_message()
                fd_list = msg.get_unix_fd_list()
                args[i] = fd_list.get(args[i])

        result = getattr(self, method_name)(*args)

        # out_args is atleast (signature1). We therefore always wrap the result
        # as a tuple. Refer to https://bugzilla.gnome.org/show_bug.cgi?id=765603
        result = (result,)

        out_args = self.method_outargs[method_name]
        if out_args != '()':
            variant = GLib.Variant(out_args, result)
            invocation.return_value(variant)
        else:
            invocation.return_value(None)

class Paginate(Server):
    """
    <!DOCTYPE node PUBLIC "-//freedesktop//DTD D-BUS Object Introspection 1.0//EN"
    "http://www.freedesktop.org/standards/dbus/1.0/introspect.dtd">
    <node>
        <interface name="com.github.dyskette.Seneca.Paginate">
            <method name="GetScrollPosition">
                <arg name="page_id" type="i" direction="in" />
                <arg name="paginate" type="b" direction="in" />
                <arg name="result" type="d" direction="out" />
            </method>
            <method name="SetScrollPosition">
                <arg name="page_id" type="i" direction="in" />
                <arg name="paginate" type="b" direction="in" />
                <arg name="position" type="d" direction="in" />
                <arg name="result" type="b" direction="out" />
            </method>
            <method name="SetScrollToFragment">
                <arg name="page_id" type="i" direction="in" />
                <arg name="paginate" type="b" direction="in" />
                <arg name="elem_id" type="s" direction="in" />
                <arg name="result" type="b" direction="out" />
            </method>
            <method name="ScrollNext">
                <arg name="page_id" type="i" direction="in" />
                <arg name="paginate" type="b" direction="in" />
                <arg name="result" type="b" direction="out" />
            </method>
            <method name="ScrollPrev">
                <arg name="page_id" type="i" direction="in" />
                <arg name="paginate" type="b" direction="in" />
                <arg name="result" type="b" direction="out" />
            </method>
            <method name="AdjustScrollPosition">
                <arg name="page_id" type="i" direction="in" />
                <arg name="paginate" type="b" direction="in" />
                <arg name="result" type="b" direction="out" />
            </method>
        </interface>
    </node>
    """

    def __init__(self, extension, level):
        """Connect to 'page-created'

        Args:
            extension (WebKit2WebExtension.WebExtension)
        """
        logging.basicConfig(level=level)
        self.extension = None
        self.bus_conn = None
        self.bus_path = '/com/github/dyskette/SenecaPaginate'
        self.bus_name = 'com.github.dyskette.Seneca.Paginate'
        self.page_bus_name = None

        extension.connect('page-created', self.on_page_created)

    def on_page_created(self, extension, web_page):
        """Connect to 'document-loaded'

        Args:
            extension (WebKit2WebExtension.WebExtension)
            web_page (WebKit2WebExtension.WebPage)
        """
        if self.page_bus_name is None:
            logger.info('Creating connection')
            self.page_bus_name = self.bus_name + '.Page%s' % web_page.get_id()
            logger.info(self.page_bus_name)

            self.bus_conn = Gio.bus_get_sync(Gio.BusType.SESSION, None)
            logger.info(self.bus_conn)

            Gio.bus_own_name_on_connection(self.bus_conn,
                                           self.page_bus_name,
                                           Gio.BusNameOwnerFlags.NONE,
                                           None,
                                           None)
            Server.__init__(self, self.bus_conn, self.bus_path)
            logger.info('Connection ready!')
        else:
            logger.warning('There exists a connection already!')

        self.extension = extension
        web_page.connect('document-loaded', self.on_document_loaded)

    def on_document_loaded(self, web_page):
        """The DOM has loaded.

        Args:
            web_page (WebKit2WebExtension.WebPage)
        """
        logger.info('DocumentLoaded:Set inner wrapper')
        document = web_page.get_dom_document()

        body = document.get_body()
        body.set_inner_html(SENECA_INNER_WRAPPER.format(body.get_inner_html()))

    def get_position(self, page_id, paginate):
        """Get scroll_x if paginate or scroll_y otherwise

        Args:
            page_id (int)
            paginate (bool)

        Returns:
            An int representing the current scroll position
        """
        web_page = self.extension.get_page(page_id)
        dom_doc = web_page.get_dom_document()
        dom_win = dom_doc.get_default_view()

        if paginate:
            position = dom_win.get_scroll_x()
        else:
            position = dom_win.get_scroll_y()

        return position

    def set_position(self, page_id, paginate, position):
        """Set arbitrary scroll position

        Args:
            page_id (int)
            paginate (bool)
            position (float)

        Returns:
            An int representing the new position
        """
        web_page = self.extension.get_page(page_id)
        dom_doc = web_page.get_dom_document()
        dom_win = dom_doc.get_default_view()

        if paginate:
            dom_win.scroll_to(position, 0.0)
            position_new = dom_win.get_scroll_x()
        else:
            dom_win.scroll_to(0.0, position)
            position_new = dom_win.get_scroll_y()

        return position_new

    def get_doc_length(self, page_id, paginate):
        """Return scroll_width if paginate or scroll_height otherwise

        Args:
            page_id (int)
            paginate (bool)

        Returns:
            A float representing the length of the document
        """
        web_page = self.extension.get_page(page_id)
        dom_doc = web_page.get_dom_document()
        dom_elem = dom_doc.get_document_element()

        if paginate:
            length = dom_elem.get_scroll_width()
        else:
            length = dom_elem.get_scroll_height()

        return float(length)

    def get_view_length(self, page_id, paginate):
        """Return width if paginate or height otherwise

        Args:
            page_id (int)
            paginate (bool)

        Returns:
            An int representing the length of the view
        """
        web_page = self.extension.get_page(page_id)
        dom_doc = web_page.get_dom_document()
        dom_win = dom_doc.get_default_view()

        if paginate:
            length = dom_win.get_inner_width()
        else:
            length = dom_win.get_inner_height()

        return length

    def adjust_position(self, position, view_length):
        """Position adjustment function.

        Go to the next page if the position given is closer to it.

        Args:
            position (int)
            view_length (int)

        Returns:
            position (int)
        """
        logger.info('Adjusting position value')
        page = position // view_length
        next = page + 1

        page_pos = view_length * page
        next_pos = view_length * next

        d1 = position - page_pos
        d2 = next_pos - position

        # The less, the better...
        if d1 < d2:
            position = page_pos
        else:
            position = next_pos

        return position

    def GetScrollPosition(self, page_id, paginate):
        """Return scroll x or y

        Args:
            page_id (int)
            paginate (bool)

        Returns:
            A float representing the current scroll position
        """
        position = self.get_position(page_id, paginate)
        doc_length = self.get_doc_length(page_id, paginate)
        return position / doc_length * 100.0

    def SetScrollPosition(self, page_id, paginate, position):
        """Set arbitrary scroll position

        Args:
            page_id (int)
            paginate (bool)
            position (float) - Percentage

        Returns:
            A boolean depending if the operation was succesful or not
        """
        doc_length = self.get_doc_length(page_id, paginate)
        view_length = self.get_view_length(page_id, paginate)
        position = int(position * doc_length / 100.0)

        last_step = doc_length - view_length
        if position >= last_step:
            position = last_step
        elif position <= 0:
            position = 0
        else:
            position = self.adjust_position(position, view_length)

        position_result = self.set_position(page_id, paginate, position)

        if position == position_result:
            pos_str = str(position_result / doc_length * 100.0)
            logger.info('Set position result:' + pos_str)
            return True

        return False

    def SetScrollToFragment(self, page_id, paginate, elem_id):
        """Scroll to element id

        Args:
            page_id (int)
            paginate (bool)
            elem_id (str)

        Returns:
            A boolean depending if the operation was succesful or not
        """
        web_page = self.extension.get_page(page_id)
        dom_doc = web_page.get_dom_document()
        dom_elem = dom_doc.get_element_by_id(elem_id)

        if not dom_elem:
            return False

        if paginate:
            position_elem = dom_elem.get_offset_left()
        else:
            position_elem = dom_elem.get_offset_top()

        view_length = self.get_view_length(page_id, paginate)
        position = (position_elem // view_length) * view_length
        half_view = view_length // 2
        if position_elem > position + half_view:
            position = (position_elem // half_view) * half_view

        position_result = self.set_position(page_id, paginate, position)

        if position == position_result:
            doc_length = self.get_doc_length(page_id, paginate)
            pos_str = str(position_result / doc_length * 100.0)
            logger.info('Fragment position result:' + pos_str)
            return True

        return False

    def ScrollNext(self, page_id, paginate):
        """Scroll to next position

         Args:
            page_id (int)
            paginate (bool)

        Returns:
            A boolean depending if the operation was succesful or not
        """
        position = self.get_position(page_id, paginate)
        doc_length = self.get_doc_length(page_id, paginate)
        view_length = self.get_view_length(page_id, paginate)
        position = position + view_length

        if position >= doc_length:
            return False

        last_step = doc_length - view_length
        if position > last_step:
            position = last_step
        else:
            position = self.adjust_position(position, view_length)

        position_result = self.set_position(page_id, paginate, position)

        if position == position_result:
            pos_str = str(position_result / doc_length * 100.0)
            logger.info('Next position result:' + pos_str)
            return True

        return False

    def ScrollPrev(self, page_id, paginate):
        """Return scroll x or y

        Args:
            page_id (int)
            paginate (bool)

        Returns:
            A boolean depending if the operation was succesful or not
        """
        position = self.get_position(page_id, paginate)
        doc_length = self.get_doc_length(page_id, paginate)
        view_length = self.get_view_length(page_id, paginate)

        last_step = (doc_length // view_length - 1) * view_length
        if position > last_step:
            position = last_step
        else:
            position = position - view_length

        if position < 0:
            return False

        position = self.adjust_position(position, view_length)
        position_result = self.set_position(page_id, paginate, position)

        if position == position_result:
            pos_str = str(position_result / doc_length * 100.0)
            logger.info('Prev position result:' + pos_str)
            return True

        return False

    def AdjustScrollPosition(self, page_id, paginate):
        """Use adjust_position() to fix view positioning.

        Args:
            page_id (int)
            paginate (bool)

        Returns:
            A boolean depending if the operation was succesful or not
        """
        position = self.get_position(page_id, paginate)
        doc_length = self.get_doc_length(page_id, paginate)
        view_length = self.get_view_length(page_id, paginate)

        position = self.adjust_position(position, view_length)
        position_result = self.set_position(page_id, paginate, position)

        if position == position_result:
            pos_str = str(position_result / doc_length * 100.0)
            logger.info('Adjust position result:' + pos_str)
            return True

        return False
