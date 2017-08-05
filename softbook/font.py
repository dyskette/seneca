# font.py
#
# Copyright (C) 2017 Dylan Smith
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

import gi
from gi.repository import Pango

class pangoFont:

    def __init__(self, fontfamily, fontweight, fontstyle, fontstretch, fontsize):
        """Returns a pango font description

        Parameters:
            fontfamily (str): 'Fira Sans', 'Sans', 'Mono', etc...
            fontweight (int): '100', '200', '300'... '900'
            fontstyle (str): 'normal', 'italic' or 'oblique'
            fontstretch (str): ...'condensed', 'normal', 'expanded'...
            fontsize (int)

        Returns:
            Pango.FontDescription
        """

        __fstring = '{0} {1} {2} {3} {4}'.format(fontfamily,
                                                 fontweight,
                                                 fontstyle,
                                                 fontstretch,
                                                 fontsize)
        self.desc = Pango.FontDescription.from_string(__fstring)
        print(__fstring)
        print(self.desc.get_family())
        print(self.desc.get_weight())
        print(self.desc.get_style())
        print(self.desc.get_stretch())
        print(self.desc.get_size())

class cssFont:

    def __init__(self, pango_fontdesc):
        self.family = pango_fontdesc.get_family()
        self.weight = pango_fontdesc.get_weight().numerator
        self.style = pango_fontdesc.get_style().value_nick
        self.stretch = pango_fontdesc.get_stretch().value_nick
        self.size = int(round(pango_fontdesc.get_size()/Pango.SCALE))
