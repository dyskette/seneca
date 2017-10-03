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

import os
import logging
logger = logging.getLogger(name='webextensions.pagination')

import gi
from gi.repository import Gio, GLib

# Shamelessly copied from GNOME Music
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
            <method name="GetScrollLength">
                <arg name="page_id" type="i" direction="in" />
                <arg name="paginate" type="b" direction="in" />
                <arg name="result" type="i" direction="out" />
            </method>
            <method name="GetScrollPosition">
                <arg name="page_id" type="i" direction="in" />
                <arg name="paginate" type="b" direction="in" />
                <arg name="result" type="i" direction="out" />
            </method>
            <method name="SetScrollPosition">
                <arg name="page_id" type="i" direction="in" />
                <arg name="paginate" type="b" direction="in" />
                <arg name="position" type="i" direction="in" />
                <arg name="result" type="i" direction="out" />
            </method>
            <method name="SetScrollToId">
                <arg name="page_id" type="i" direction="in" />
                <arg name="paginate" type="b" direction="in" />
                <arg name="elem_id" type="s" direction="in" />
                <arg name="result" type="i" direction="out" />
            </method>
        </interface>
    </node>
    """

    def __init__(self, extension, level):
        """Connect to 'page-created'

        Args:
            extension (WebKit2WebExtension.WebExtension)
        """
        self.extension = None
        self.bus_conn = None
        self.bus_path = '/com/github/dyskette/Seneca/Paginate'
        self.bus_name = 'com.github.dyskette.Seneca.Paginate'
        self.page_bus_name = None
        logging.basicConfig(level=level)
        logger.info('Class paginate init')
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

        self.extension = extension

    def GetScrollLength(self, page_id, paginate):
        """Return width or height

        Args:
            page_id (int)
            paginate (bool)

        Returns:
            An int representing the internal width or height of the document
        """
        web_page = self.extension.get_page(page_id)
        dom_doc = web_page.get_dom_document()
        dom_elem = dom_doc.get_document_element()

        if paginate:
            length = dom_elem.get_scroll_width()
        else:
            length = dom_elem.get_scroll_height()

        return length

    def GetScrollPosition(self, page_id, paginate):
        """Return scroll x

        Args:
            page_id (int)
            paginate (bool)

        Returns:
            An int representing the current horizontal position
        """
        web_page = self.extension.get_page(page_id)
        dom_doc = web_page.get_dom_document()
        dom_win = dom_doc.get_default_view()

        if paginate:
            position = dom_win.get_scroll_x()
        else:
            position = dom_win.get_scroll_y()

        return position

    def SetScrollPosition(self, page_id, paginate, position):
        """Set arbitrary scroll position

        Args:
            page_id (int)
            paginate (bool)
            position (int)

        Returns:
            An int representing the new position in the document
        """
        web_page = self.extension.get_page(page_id)
        dom_doc = web_page.get_dom_document()
        dom_win = dom_doc.get_default_view()

        position = float(position)
        if paginate:
            dom_win.scroll_to(position, 0.0)
            position_new = dom_win.get_scroll_x()
        else:
            dom_win.scroll_to(0.0, position)
            position_new = dom_win.get_scroll_y()

        return position_new

    def SetScrollToId(self, page_id, paginate, elem_id):
        """Scroll to element id

        Args:
            page_id (int)
            paginate (bool)
            elem_id (str)

        Returns:
            An int representing the new position in the document
        """
        web_page = self.extension.get_page(page_id)
        dom_doc = web_page.get_dom_document()
        dom_win = dom_doc.get_default_view()
        dom_elem = dom_doc.get_element_by_id(elem_id)

        if not dom_elem:
            return 0

        dom_elem.scroll_into_view_if_needed(True)
        if paginate:
            position_new = dom_win.get_scroll_x()
        else:
            position_new = dom_win.get_scroll_y()

        return position_new
