# dbus_helper.py
#
# Copyright © 2018 Eddy Castillo
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

logger = logging.getLogger(__name__)
APP_DEFAULT = Gio.Application.get_default
PROXY_BUS = 'com.github.dyskette.Seneca.Paginate.Page%s'
PROXY_PATH = '/com/github/dyskette/SenecaPaginate'
PROXY_INTERFACE = 'com.github.dyskette.Seneca.Paginate'


class DBusHelper:

    def __init__(self):
        self.__signals = {}

    def call(self, call: str, page_id: int,
             dbus_args: GLib.Variant = None,
             callback: object = None,
             *args: str):
        """
        Call function to create proxy to access methods

        :param call:
        :param page_id:
        :param dbus_args:
        :param callback:
        :param args:
        """
        try:
            bus = APP_DEFAULT().get_dbus_connection()
            proxy_bus = PROXY_BUS % page_id
            Gio.DBusProxy.new(bus, Gio.DBusProxyFlags.NONE, None,
                              proxy_bus,
                              PROXY_PATH,
                              PROXY_INTERFACE, None,
                              self._on_get_proxy,
                              call, dbus_args, callback, *args)
        except Exception as e:
            logger.error("DBusHelper::call():", e)

    def connect(self, signal: str, callback: object, page_id: int):
        """
        Connect callback to object signals

        :param signal:
        :param callback:
        :param page_id:
        """
        try:
            bus = APP_DEFAULT().get_dbus_connection()
            proxy_bus = PROXY_BUS % page_id
            subscribe_id = bus.signal_subscribe(None, proxy_bus, signal,
                                                PROXY_PATH, None,
                                                Gio.DBusSignalFlags.NONE,
                                                callback)
            self.__signals[page_id] = (bus, subscribe_id)
        except Exception as e:
            print("DBusHelper::connect():", e)

    def disconnect(self, page_id: int):
        """
        Disconnect signal

        :param page_id:
        """
        if page_id in self.__signals.keys():
            (bus, subscribe_id) = self.__signals[page_id]
            bus.signal_unsubscribe(subscribe_id)
            del self.__signals[page_id]

    def _on_get_proxy(self,
                      source: Gio.DBusProxy, result: Gio.AsyncResult,
                      call: str, dbus_args: GLib.Variant, callback: object,
                      *args: str):
        """
        Launch call and connect it to callback

        :param source:
        :param result:
        :param call:
        :param dbus_args:
        :param callback:
        :param args:
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
