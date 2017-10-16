# epub.py
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

from gettext import gettext as _

import zipfile
import posixpath
from lxml import etree

import gi
gi.require_version('Soup', '2.4')
from gi.repository import GLib, GObject, Soup

from .book_error import BookError

OASIS = '{urn:oasis:names:tc:opendocument:xmlns:container}'
OPF = '{http://www.idpf.org/2007/opf}'
DC = '{http://purl.org/dc/elements/1.1/}'
DAISY = '{http://www.daisy.org/z3986/2005/ncx/}'
XHTML = '{http://www.w3.org/1999/xhtml}'
EPUB = '{http://www.idpf.org/2007/ops}'
XLINK = '{http://www.w3.org/1999/xlink}'

class Epub(GObject.GObject):

    def __init__(self):
        GObject.GObject.__init__(self)

        self.version = 1.2
        self.metadata = {}
        self.identifier = ''
        self.title = ''
        self.language = ''

        self.resources = {}
        self.cover_doc = ''
        self.cover = ''

        self.spine = []
        self.guide = []
        self.navigation = []

        self.__keys = {}
        self.__toc = ''
        self.__current = 0

        self.path = ''

    def open(self, epub_path):
        if not GLib.file_test(epub_path, GLib.FileTest.EXISTS):
            raise BookError(0, _('No such file or directory: {0}').format(epub_path))

        if not GLib.file_test(epub_path, GLib.FileTest.IS_REGULAR):
            raise BookError(0, _('Path is a directory: {0}').format(epub_path))

        try:
            archive = zipfile.ZipFile(epub_path, 'r', compression=zipfile.ZIP_DEFLATED, allowZip64=True)
        except zipfile.BadZipFile as e:
            raise BookError(0, _('Bad file: {0}').format(epub_path))
        except zipfile.LargeZipFile as e:
            raise BookError(0, _('File is too big').format(epub_path))

        try:
            assert (archive.read('mimetype') == b'application/epub+zip'), 'Wrong mimetype!'
        except (KeyError, AssertionError) as e:
            raise BookError(1, _('Not an epub file: {0}').format(epub_path))

        container = archive.read('META-INF/container.xml')
        parser = etree.XMLParser(encoding='utf-8')
        container_elem = etree.fromstring(container, parser=parser)

        # The <rootfiles> element MUST contain at least one <rootfile> element
        # that has a media-type of "application/oebps-package+xml". Only one
        # <rootfile> element with a media-type of "application/oebps-package+xml"
        # SHOULD be included. The file referenced by the first <rootfile> element
        # that has a media-type of "application/oebps-package+xml" will be
        # considered the EPUB rootfile.
        #
        # <rootfiles>
        #   <rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/>
        #

        rootfile_list = container_elem.findall('.//{0}rootfile[@media-type]'.format(OASIS))

        for rootfile in rootfile_list:
            if rootfile.get('media-type') == 'application/oebps-package+xml':
                opf_path = rootfile.get('full-path')
                break

        self.path = epub_path
        self._process_opf_file(archive, opf_path)

    def _process_opf_file(self, archive, opf_path):
        epub_opf = archive.read(opf_path)
        parser = etree.XMLParser(encoding='utf-8')
        opf_elem = etree.fromstring(epub_opf, parser=parser)

        self.version = float(opf_elem.get('version'))

        # identity
        if opf_elem.get('unique-identifier'):
            unique_id = opf_elem.get('unique-identifier')

        # metadata
        metadata_elem = opf_elem.find('{0}metadata'.format(OPF))
        for child in metadata_elem:
            if not etree.iselement(child) or child.tag is etree.Comment:
                continue

            tag = child.tag[child.tag.rfind('}') + 1:]

            if child.prefix and child.prefix.lower() == 'dc':
                if tag == 'identifier' and child.get('id') == unique_id:
                    self.identifier = child.text

                if self.metadata.get(tag, None):
                    self.metadata[tag].append(child.text)
                else:
                    self.metadata[tag] = [child.text]

        self.title = self.metadata.get('title', [''])[0]
        self.language =  self.metadata.get('language', [''])[0]

        # manifest
        # TODO: Check OPS Core Media Types
        # MIME Media Type           Description
        # image/gif	                Used for raster graphics
        # image/jpeg                Used for raster graphics
        # image/png                 Used for raster graphics
        # image/svg+xml             Used for vector graphics
        # application/xhtml+xml     Used for OPS Content Documents
        # application/x-dtbook+xml  Used for OPS Content Documents
        # text/css                  Used for OPS CSS-subset style sheets
        # application/xml           Used for Out-Of-Line XML Islands
        # text/x-oeb1-document      Deprecated; Used for Basic or Extended OEBPS 1.0.1 and 1.2 Documents
        # text/x-oeb1-css           Deprecated; Used for OEBPS 1.0.1 and 1.2 CSS-subset style sheets
        # application/x-dtbncx+xml  The NCX
        #
        # Do not render img or object elements of unsupported media types, in the absence of fallbacks.
        img_types = ['image/gif', 'image/jpeg', 'image/jpg', 'image/png', 'image/svg+xml']
        opf_dir_path = posixpath.dirname(opf_path)

        manifest_elem = opf_elem.find('{0}manifest'.format(OPF))
        for child in manifest_elem:
            if not etree.iselement(child) and child.tag != '{0}item'.format(OPF):
                continue

            if isinstance(child, etree._Comment):
                continue

            props = child.get('properties', '')
            if props:
                res_props = props.split(' ')
            else:
                res_props = []

            res_type = child.get('media-type')
            res_id = child.get('id')
            res_path = posixpath.join(opf_dir_path, child.get('href'))
            res_content = archive.read(res_path)

            self.resources[res_path] = (res_id, res_content, res_type, res_props)
            self.__keys[res_id] = res_path

            if res_type == 'application/xhtml+xml':
                if 'nav' in res_props:
                    self.__toc = res_path
                elif 'cover' in res_props:
                    self.cover_doc = res_path
            elif res_type in img_types:
                if 'cover-image' in res_props:
                    self.cover_img = res_path

        # spine
        # TODO: Figure out what to do when linear="no"
        # Maybe we should ignore the first item if it has that attr. (as kindle)
        spine_elem = opf_elem.find('{0}spine'.format(OPF))

        ncx_id = spine_elem.get('toc')
        if ncx_id:
            if not self.__toc:
                self.__toc = self.__keys[ncx_id]

        ppd = spine_elem.get('page-progression-direction')
        if ppd:
            self.direction = ppd
        else:
            self.direction = 'default'

        for child in spine_elem:
            if not etree.iselement(child) and child.tag != '{0}itemref'.format(OPF):
                continue

            _id = child.get('idref')
            # linear = child.get('linear', 'yes')
            self.spine.append(self.__keys[_id])

        # guide
        guide_elem = opf_elem.find('{0}guide'.format(OPF))

        if guide_elem is not None:
            for child in guide_elem:
                if not etree.iselement(child) and child.tag != '{0}reference'.format(OPF):
                    continue

                ref_type = child.get('type')
                ref_title = child.get('title')
                ref_href = posixpath.join(opf_dir_path, child.get('href'))

                self.guide.append((ref_href, ref_title, ref_type))

                if ref_type == 'cover':
                    if not self.cover_doc:
                        self.cover_doc = ref_href

        # landmarks
        if self.version == 3.0:
            pass

    def _bytes_to_elem(self, content_bytes, html=True):
        if html:
            parser = etree.HTMLParser(encoding='utf-8')
        else:
            parser = etree.XMLParser(encoding='utf-8')
        elem = etree.fromstring(content_bytes, parser=parser)
        return elem

    def _get_path_fragment(self, _path):
        path = ''
        fragment = ''

        if _path:
            soup_uri = Soup.URI.new(_path)
            path = soup_uri.get_path()[1:]
            fragment = soup_uri.get_fragment() or ''

        return [path, fragment]

    def _parse_ncx(self, toc_elem, toc_treestore):
        navmap = toc_elem.find('{0}navMap'.format(DAISY))

        def get_children(item, parent_iter):
            title = item.find('{D}navLabel/{D}text'.format(D=DAISY)).text
            _path = item.find('{0}content'.format(DAISY)).get('src', '')
            path, fragment = self._get_path_fragment(_path)

            item_iter = toc_treestore.append(parent_iter, [title, path, fragment])

            children = item.findall('{0}navPoint'.format(DAISY))
            if children:
                for child in children:
                    get_children(child, item_iter)

        for child in navmap.getchildren():
            get_children(child, None)

    def _parse_nav(self, toc_elem, toc_treestore):
        navs = toc_elem.findall('{X}body/{X}nav'.format(X=XHTML))

        def get_children(item, parent_iter):
            url = item.find('{0}a'.format(XHTML))
            title = url.text
            _path = url.get('href')
            path, fragment = self._get_path_fragment(_path)

            item_iter = toc_treestore.append(parent_iter, [title, path, fragment])

            ol = item.find('{0}ol'.format(XHTML))
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

    def populate_store(self, toc_treestore):
        toc_bytes = self.get_resource_with_epub_uris(self.__toc, False)
        toc_elem = self._bytes_to_elem(toc_bytes, False)

        if toc_elem.tag == '{0}ncx'.format(DAISY):
            self._parse_ncx(toc_elem, toc_treestore)
        elif toc_elem.tag == '{0}html'.format(XHTML):
            self._parse_nav(toc_elem, toc_treestore)

    def is_navigation_type(self, path):
        mime = self.get_resource_mime(path)
        if mime.endswith('xml'):
            return True
        else:
            return False

    def _replace_uris(self, path, content_bytes, html):
        elem = self._bytes_to_elem(content_bytes, html)

        def set_epub_uri(tag, attr, ns):
            if path:
                path_base = 'epub:///{0}/'.format(path)
            else:
                path_base = 'epub:///'
            soup_base = Soup.URI.new(path_base)

            if ns:
                attrname = '{0}{1}'.format(ns, attr)
            else:
                attrname = attr

            tag_str = '{*}' + tag
            elem_iter = elem.iter(tag_str)
            for e in elem_iter:
                # If element is inside <pre> tag, skip.
                asc_iter = e.iterancestors('{*}pre')
                has_pre = False
                for asc in asc_iter:
                    has_pre = True
                    break

                if has_pre:
                    continue

                attr_content = e.get(attrname)
                if attr_content:
                    if attr_content.startswith('#'):
                        soup_uri = Soup.URI.new_with_base(Soup.URI.new('epub:///'), attr_content)
                    else:
                        soup_uri = Soup.URI.new_with_base(soup_base, attr_content)
                    uri = soup_uri.to_string(False)
                    e.set(attrname, uri)

        set_epub_uri('link', 'href', None)
        set_epub_uri('img', 'src', None)
        set_epub_uri('image', 'href', XLINK)
        set_epub_uri('a', 'href', None)
        set_epub_uri('content', 'src', None)

        content_bytes = etree.tostring(elem)
        return content_bytes

    def get_resource_path(self, _id):
        try:
            return self.__keys[_id]
        except KeyError as e:
            raise BookError('Wrong id or resource does not exist')

    def try_resource(self, path, i):
        try:
            return self.resources[path][i]
        except KeyError as e:
            raise BookError('Wrong path or resource does not exist')

    def get_resource_id(self, path):
        return self.try_resource(path, 0)

    def get_resource(self, path):
        return self.try_resource(path, 1)

    def get_resource_mime(self, path):
        return self.try_resource(path, 2)

    def get_resource_with_epub_uris(self, path, html=True):
        content = self.get_resource(path)
        dirname = posixpath.dirname(path)
        replace = self._replace_uris(dirname, content, html)
        return replace

    def get_n_pages(self):
        return len(self.spine)

    @GObject.Property(type=int)
    def page(self):
        return self.__current

    @page.setter
    def page(self, page):
        if not isinstance(page, int):
            raise BookError('Wrong value type for page, should be int')

        if page >= 0 and page < len(self.spine):
            self.__current = page
        else:
            raise BookError('Value out of range: 0 to {0}'.format(len(self.spine)))

    def go_prev(self):
        if self.__current == 0:
            raise BookError('Value out of range: 0 to {0}'.format(len(self.spine)))

        self.page = self.__current - 1

    def go_next(self):
        if self.__current == len(self.spine) - 1:
            raise BookError('Value out of range: 0 to {0}'.format(len(self.spine)))

        self.page = self.__current + 1

    def get_page(self):
        return self.page

    def set_page(self, i):
        self.page = i

    def set_page_by_path(self, path):
        if path in self.spine:
            logger.info('Path found in spine')
            i = self.spine.index(path)
            self.set_page(i)
        else:
            logger.info('Path not found in spine')

    def get_current_path(self):
        return self.spine[self.__current]

    def get_current_id(self):
        path = self.get_current_path()
        return self.get_resource_id(path)

    def get_current(self):
        path = self.get_current_path()
        return self.get_resource(path)

    def get_current_mime(self):
        path = self.get_current_path()
        return self.get_resource_mime(path)

    def get_current_with_epub_uris(self):
        path = self.get_current_path()
        return self.get_resource_with_epub_uris(path)

    def get_metadata(self, _id):
        return self.metadata.get(_id)

    def find_text(self, search_text):
        logger.info('Searching "{}" in epub resources'.format(search_text))

        found_list = []
        for path in self.spine:
            res = self.get_resource(path)
            res_elem = self._bytes_to_elem(res)
            res_body = res_elem.xpath('//*[local-name() = "body"]')

            for body in res_body:
                body_text = ''
                for child in body.iter():
                    if child.text and not isinstance(child, etree._Comment):
                        body_text += child.text

                found = search_text.lower() in body_text.lower()

            found_list.append([path, found])

        return found_list
