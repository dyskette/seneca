# settings.py
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
import configparser

class Settings:
    def __init__(self):
        app = 'softbook'
        self.path = os.path.join(os.path.expanduser('~'), '.config', app, 'settings.ini')
        self.conf = configparser.ConfigParser()

        self.default = {'margin' : '20',
                        'color' : 'light',
                        'fontfamily' : 'Sans',
                        'fontweight' : '400',
                        'fontstyle' : 'normal',
                        'fontstretch' : 'normal',
                        'fontsize' : '20',
                        'lineheight' : '1.6',
                        'paginate' : 'yes',
                        'maximized' : 'no',
                        'winheight' : '600',
                        'winwidth' : '800'}

        self.colors = {}
        self.colors['light'] = {'foreground': '#333333',
                                'background': '#ffffff'}
        self.colors['sepia'] = {'foreground': '#5b4636',
                                'background': '#f4ecd8'}
        self.colors['dark'] = {'foreground': '#eeeeee',
                               'background': '#232729'}

        self.load()

    def load(self):
        if os.path.exists(self.path):
            self.conf.read(self.path)
        else:
            _dir = os.path.split(self.path)[0]
            if not os.path.exists(_dir):
                os.makedirs(_dir)

            self.conf['Settings'] = self.default
            self.save()

    def save(self):
        with open(self.path, 'w') as configfile:
            self.conf.write(configfile)

    def get_book(self, identifier):
        return identifier in self.conf

    def add_book(self, identifier):
        self.conf[identifier] = {}
        self.conf[identifier]['chapter'] = '0'
        self.conf[identifier]['position'] = '0'

    def save_pos(self, identifier, chapter, position):
        self.conf[identifier]['chapter'] = str(chapter)
        self.conf[identifier]['position'] = str(position)

    def get_chapter(self, identifier):
        return int(self.conf[identifier]['chapter'])

    def get_position(self, identifier):
        return int(self.conf[identifier]['position'])

    @property
    def margin(self):
        return int(self.conf['Settings']['margin'])

    @margin.setter
    def margin(self, value):
        self.conf['Settings']['margin'] = str(value)

    @property
    def color(self):
        return self.conf['Settings']['color']

    @color.setter
    def color(self, value):
        self.conf['Settings']['color'] = value

    @property
    def color_fg(self):
        return self.colors[self.color]['foreground']

    @color_fg.setter
    def color_fg(self, value):
        self.colors[self.color]['foreground'] = value

    @property
    def color_bg(self):
        return self.colors[self.color]['background']

    @color_bg.setter
    def color_bg(self, value):
        self.colors[self.color]['background'] = value

    @property
    def fontfamily(self):
        return self.conf['Settings']['fontfamily']

    @fontfamily.setter
    def fontfamily(self, value):
        self.conf['Settings']['fontfamily'] = value

    @property
    def fontweight(self):
        return int(self.conf['Settings']['fontweight'])

    @fontweight.setter
    def fontweight(self, value):
        self.conf['Settings']['fontweight'] = str(value)

    @property
    def fontstyle(self):
        return self.conf['Settings']['fontstyle']

    @fontstyle.setter
    def fontstyle(self, value):
        self.conf['Settings']['fontstyle'] = value

    @property
    def fontstretch(self):
        return self.conf['Settings']['fontstretch']

    @fontstretch.setter
    def fontstretch(self, value):
        self.conf['Settings']['fontstretch'] = value

    @property
    def fontsize(self):
        return int(self.conf['Settings']['fontsize'])

    @fontsize.setter
    def fontsize(self, value):
        self.conf['Settings']['fontsize'] = str(value)

    @property
    def lineheight(self):
        return float(self.conf['Settings']['lineheight'])

    @lineheight.setter
    def lineheight(self, value):
        self.conf['Settings']['lineheight'] = str(value)

    @property
    def paginate(self):
        return self.conf['Settings'].getboolean('paginate')

    @paginate.setter
    def paginate(self, value):
        value = 'yes' if value else 'no'
        self.conf['Settings']['paginate'] = value

    @property
    def maximized(self):
        return self.conf['Settings'].getboolean('paginate')

    @maximized.setter
    def maximized(self, value):
        value = 'yes' if value else 'no'
        self.conf['Settings']['maximized'] = value

    @property
    def height(self):
        return int(self.conf['Settings']['height'])

    @height.setter
    def height(self, value):
        self.conf['Settings']['height'] = str(value)

    @property
    def width(self):
        return int(self.conf['Settings']['width'])

    @width.setter
    def width(self, value):
        self.conf['Settings']['width'] = str(value)
