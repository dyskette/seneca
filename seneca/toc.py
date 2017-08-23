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

import logging
logger = logging.getLogger(__name__)

import posixpath
from lxml import etree

PATH_COL = 1
FRAG_COL = 2

class Toc:

    def __init__(self, book, treeview, treestore):
        self.book = book
        self.treeview = treeview
        self.treestore = treestore

        selection = self.treeview.get_selection()
        selection.connect('changed', self.on_selection_changed)

    def on_selection_changed(self, selection):
        logger.info('Selection changed')
        treemodel, treeiter = selection.get_selected()

        if treeiter:
            path, fragment = treemodel.get(treeiter, PATH_COL, FRAG_COL)

            logger.info('Path: {0}'.format(path))
            self.book.jump_to_path_fragment(path, fragment)

    def initialize_selection(self, current_path):
        logger.info('Selecting active chapter in treeview')
        selection = self.treeview.get_selection()
        selection.disconnect_by_func(self.on_selection_changed)

        storeiter = self.treestore.get_iter_first()
        while storeiter != None:
            path = self.treestore.get(storeiter, PATH_COL)[0]
            if current_path in path:
                logger.info('Path found in tree: {0}'.format(current_path))
                break

            iter_parent = self.treestore.iter_parent(storeiter)
            iter_children = self.treestore.iter_children(storeiter)
            iter_next = self.treestore.iter_next(storeiter)

            if iter_children:
                storeiter = iter_children
            elif not iter_next and iter_parent:
                iter_next = self.treestore.iter_next(iter_parent)
                storeiter = iter_next
            else:
                storeiter = iter_next
        else:
            logger.info('Path not found in tree: {0}'.format(current_path))

        if storeiter:
            treepath = self.treestore.get_path(storeiter)
            self.treeview.expand_to_path(treepath)
            selection.select_iter(storeiter)
        else:
            selection.unselect_all()
            self.treeview.do_unselect_all(self.treeview)

        selection.connect('changed', self.on_selection_changed)

    def populate_store(self):
        logger.info('Populating tree store')
        self.treestore.clear()
        doc = self.book.get_doc()
        doc.populate_store(self.treestore)

        current_path = self.book.get_current_path()
        self.initialize_selection(current_path)
