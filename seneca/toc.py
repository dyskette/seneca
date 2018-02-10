# toc.py
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

import gi

gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GObject

from .gi_composites import GtkTemplate

PATH_COL = 1
FRAG_COL = 2


@GtkTemplate(ui='/com/github/dyskette/Seneca/ui/toc-dialog.ui')
class TocDialog(Gtk.Dialog):
    __gtype_name__ = 'TocDialog'

    toc_treeview = GtkTemplate.Child()
    toc_treestore = GtkTemplate.Child()

    __gsignals__ = {
        'toc-item-activated': (GObject.SIGNAL_RUN_FIRST, None, (str, str)),
    }

    def __init__(self, window):
        Gtk.Dialog.__init__(self, transient_for=window, modal=True)
        self.init_template()

    def populate_store(self, toc_list):
        def child_store(list_child, parent_iter):
            title = list_child.get('title')
            path = list_child.get('path')
            fragment = list_child.get('fragment')

            item_iter = self.toc_treestore.append(parent_iter,
                                                  [title, path, fragment])

            children = list_child.get('children')
            if not children:
                return

            for child_row in children:
                child_store(child_row, item_iter)

        for toc_row in toc_list:
            child_store(toc_row, None)

        self.toc_treeview.set_model(self.toc_treestore)

    def select_active_chapter(self, chapter_path, fragment):
        # TODO: Implement function
        pass

    @GtkTemplate.Callback
    def on_toc_treeview_row_activated(self, treeview, path, treeview_column):
        model = treeview.get_model()
        if model is None:
            return

        treeiter = model.get_iter(path)
        path, fragment = model.get(treeiter, PATH_COL, FRAG_COL)

        self.emit('toc-item-activated', path, fragment)
