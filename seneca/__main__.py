# __main__.py
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
import sys

def main():
    import gi
    from gi.repository import Gio

    filename = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'seneca.gresource')
    if not os.path.exists(filename):
        raise FileNotFoundError('gresource file missing: \'{0}\''.format(filename))

    resource = Gio.Resource.load(filename)
    Gio.Resource._register(resource)

    from .application import Application

    application = Application()

    try:
        ret = application.run(sys.argv)
    except SystemExit as e:
        ret = e.code

    sys.exit(ret)

if __name__ == '__main__':
    main()
