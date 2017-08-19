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

DAISY = '{http://www.daisy.org/z3986/2005/ncx/}'
XHTML = '{http://www.w3.org/1999/xhtml}'
EPUB = '{http://www.idpf.org/2007/ops}'

class Toc:

    def __init__(self, book, treeview, treestore):
        self.book = book
        self.toc_treeview = treeview
        self.toc_treestore = treestore

        self.setup_selection()

    def setup_selection(self):
        selection = self.toc_treeview.get_selection()
        selection.connect('changed', self.on_selection_changed)

    def on_selection_changed(self, selection):
        logger.info('Selection changed')
        treemodel, treeiter = selection.get_selected()
        path_col = 1

        if treeiter:
            path_tuple = self.toc_treestore.get(treeiter, path_col)
            try:
                path = path_tuple[0]
            except IndexError as e:
                logger.info('IndexError: {0}'.format(e))
            else:
                logger.info('Path: {0}'.format(path))
                self.book.jump_to_path(path)

    def initialize_selection(self, current_path):
        logger.info('Selecting active chapter in treeview')
        selection = self.toc_treeview.get_selection()
        selection.disconnect_by_func(self.on_selection_changed)

        path_col = 1
        storeiter = self.toc_treestore.get_iter_first()
        while storeiter != None:
            path_tuple = self.toc_treestore.get(storeiter, path_col)

            try:
                path = path_tuple[0]
            except IndexError as e:
                logger.info('IndexError: {0}'.format(e))
            else:
                if current_path in path:
                    break

            iter_parent = self.toc_treestore.iter_parent(storeiter)
            iter_children = self.toc_treestore.iter_children(storeiter)
            iter_next = self.toc_treestore.iter_next(storeiter)

            if iter_children:
                storeiter = iter_children
            elif not iter_next and iter_parent:
                iter_next = self.toc_treestore.iter_next(iter_parent)
                storeiter = iter_next
            else:
                storeiter = iter_next

        if storeiter:
            treepath = self.toc_treestore.get_path(storeiter)
            self.toc_treeview.expand_to_path(treepath)
            selection.select_iter(storeiter)

        selection.connect('changed', self.on_selection_changed)

    def populate_store(self):
        self.toc_treestore.clear()

        toc_type, toc = self.book.get_navigation()

        if toc_type == 'ncx':
            self.parse_ncx(toc)
        elif toc_type == 'nav':
            self.parse_nav(toc)
        else:
            logger.info('Nothing to do')
            return

        current_path = self.book.get_current_path()
        self.initialize_selection(current_path)

    def get_root(self, gbytes):
        logger.info('Getting document root')
        pybytes = gbytes.get_data()
        parser = etree.XMLParser(ns_clean=True, recover=True, encoding='utf-8')
        root = etree.fromstring(pybytes, parser=parser)

        return root

    def parse_ncx(self, ncx_bytes):
        logger.info('Parsing...')
        root = self.get_root(ncx_bytes)
        navmap = root.find('{D}navMap'.format(D=DAISY))

        def get_children(item, parent_iter):
            title = item.find('{D}navLabel/{D}text'.format(D=DAISY)).text
            path = item.find('{D}content'.format(D=DAISY)).get('src', '')
            children = item.findall('{D}navPoint'.format(D=DAISY))

            item_iter = self.toc_treestore.append(parent_iter, [title, path])

            if children:
                for child in children:
                    get_children(child, item_iter)

        for child in navmap.getchildren():
            get_children(child, None)

    def parse_nav(self, nav_bytes):
        logger.info('Parsing...')
        root = self.get_root(nav_bytes)
        navs = root.findall('{X}body/{X}nav'.format(X=XHTML))

        def get_children(item, parent_iter):
            url = item.find('{0}a'.format(XHTML))

            title = url.text
            path = posixpath.normpath(url.get('href'))
            ol = item.find('{0}ol'.format(XHTML))

            item_iter = self.toc_treestore.append(parent_iter, [title, path])

            if ol is not None:
                li = ol.findall('{0}li'.format(XHTML))
                for child in li:
                    get_children(child, item_iter)

        for nav in navs:
            if nav.get('{0}type'.format(EPUB)) == 'toc':
                ol = nav.find('{0}ol'.format(XHTML))
                li = ol.findall('{0}li'.format(XHTML))
                for child in li:
                    get_children(child, None)
