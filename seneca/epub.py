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

import html as python_html
import posixpath
import sys
import zipfile
import gi

gi.require_version('Soup', '2.4')
from gi.repository import GLib, GObject, Soup
from gettext import gettext as _
from lxml import etree
from lxml import html

from .book_error import BookError

OASIS = '{urn:oasis:names:tc:opendocument:xmlns:container}'
OPF = '{http://www.idpf.org/2007/opf}'
DC = '{http://purl.org/dc/elements/1.1/}'
DAISY = '{http://www.daisy.org/z3986/2005/ncx/}'
XHTML = '{http://www.w3.org/1999/xhtml}'
EPUB = '{http://www.idpf.org/2007/ops}'
XLINK = '{http://www.w3.org/1999/xlink}'


class Epub(GObject.GObject):

    def __init__(self) -> None:
        GObject.GObject.__init__(self)

        self.version = 1.2
        self.metadata = {}
        self.identifier = ''
        self.title = ''
        self.language = ''

        self.resources = {}
        self.resources_by_id = {}
        self.cover_doc = ''
        self.cover = ''

        self.direction = 'default'
        self.spine_primary = []
        self.spine_auxiliary = []
        self.guide = []
        self.navigation = []
        self.pages_positions = []

        self.toc_path = ''
        self.path = ''

        self.__current = 0

    def open(self, epub_path: str):
        """
        Open an epub file from the path provided

        :param epub_path: The path to the epub file
        :raises BookError: When the file or format is incorrect.
        """
        if not GLib.file_test(epub_path, GLib.FileTest.EXISTS):
            raise BookError(0, _('File does not exist'), epub_path)

        if not GLib.file_test(epub_path, GLib.FileTest.IS_REGULAR):
            raise BookError(0, _('Is a directory'), epub_path)

        epub_zip = self._open_zip_archive(epub_path)

        if epub_zip is None:
            raise BookError(0, _('Could not read zip format'), epub_path)

        if not self._has_epub_mime(epub_zip):
            raise BookError(0, _('Unrecognized file format'), epub_path)

        try:
            opf_path = self._read_opf_path(epub_zip)
            if opf_path is None:
                raise BookError(0, '')
        except BookError:
            raise BookError(0, _('Broken or missing OPF file'), epub_path)

        try:
            opf_content = self._read_inner_zip_path(epub_zip, opf_path)
        except BookError:
            raise BookError(0, _('Could not read OPF file'), epub_path)

        opf_mime = 'application/oebps-package+xml'
        opf_elem = self._bytes_to_elem(opf_content, opf_mime)
        opf_elem = opf_elem.getroot()

        self.version = opf_elem.get('version')
        self.metadata = self._get_opf_metadata(opf_elem)
        self.identifier = self.metadata.get('identifier', [''])[0]
        self.title = self.metadata.get('title', [''])[0]
        self.language = self.metadata.get('language', [''])[0]

        opf_resources = self._get_opf_resources(opf_path, opf_elem, epub_zip)
        self.resources = opf_resources[0]
        self.resources_by_id = opf_resources[1]
        self.cover_doc = ''
        self.cover = ''

        # TODO: Cover EPUB2 (from OPF manifest)
        #         img_types = [
        #             'image/gif',
        #             'image/jpeg',
        #             'image/jpg',
        #             'image/png',
        #             'image/svg+xml'
        #         ]
        #         if res_type in img_types:
        #             if 'cover-image' in res_props:
        #                 self.cover_img = res_path
        #
        # TODO: Cover EPUB3 (from OPF manifest)
        #         if res_type == 'application/xhtml+xml':
        #             elif 'cover' in res_props:
        #                 self.cover_doc = res_path
        #
        # TODO: Cover EPUB3 (from guide)
        #                 if ref_type == 'cover':
        #                     if not self.cover_doc:
        #                         self.cover_doc = ref_href

        self.direction = self._get_opf_progression_direction(opf_elem)
        self.spine_primary, self.spine_auxiliary = self._get_opf_spine(opf_elem)
        self.guide = self._get_opf_guide(opf_path, opf_elem)
        # TODO: self.navigation = self._get_opf_navigation(opf_elem)
        self.pages_positions = self._calculate_pages_positions()

        self.toc_path = self._get_toc_path(opf_elem)
        self.path = epub_path

    def get_toc(self) -> list:
        """
        Find the table of contents and returns it

        :return: The table of contents as a list of dictionaries
        """
        toc_bytes = self.get_resource_with_epub_uris(self.toc_path)
        toc_mime = self.get_resource_mime(self.toc_path)
        toc_elem = self._bytes_to_elem(toc_bytes, toc_mime)

        if toc_elem.getroot().tag == '{0}ncx'.format(DAISY):
            return self._parse_ncx(toc_elem)
        elif toc_elem.getroot().tag == '{0}html'.format(XHTML):
            return self._parse_nav(toc_elem)

        return []

    def _raise_resource_not_found(self, message: str):
        """
        Helper function to raise common exception

        :param message: The id or path of the resource
        """
        raise BookError(1, _('Resource not found') + ' «' + message + '»')

    def get_resource_path(self, resource_id: str) -> str:
        """
        Obtain the path of the given resource id

        :param resource_id: An id of a resource
        :return: The path to the resource
        """
        try:
            return self.resources_by_id[resource_id]
        except KeyError as e:
            self._raise_resource_not_found(e.args[0])

    def get_resource_id(self, path: str) -> str:
        try:
            return self.resources[path]['id']
        except KeyError as e:
            self._raise_resource_not_found(e.args[0])

    def get_resource_content(self, path: str) -> bytes:
        try:
            return self.resources[path]['content']
        except KeyError as e:
            self._raise_resource_not_found(e.args[0])

    def get_resource_mime(self, path: str) -> str:
        try:
            return self.resources[path]['mimetype']
        except KeyError as e:
            self._raise_resource_not_found(e.args[0])

    def get_resource_with_epub_uris(self, resource_path):
        content = self.get_resource_content(resource_path)
        mimetype = self.get_resource_mime(resource_path)
        replace = self._replace_uris(resource_path, content, mimetype)
        return replace

    def is_page(self, path):
        if (path in self.spine_primary or path in self.spine_auxiliary):
            return True

        return False

    def get_n_pages(self):
        return len(self.spine_primary)

    @GObject.Property(type=int)
    def page(self):
        return self.__current

    @page.setter
    def page(self, page):
        if page < 0 or page >= len(self.spine_primary):
            return

        self.__current = page

    def go_prev(self):
        prev_page = self.__current - 1
        if prev_page < 0:
            raise IndexError

        self.page = prev_page

    def go_next(self):
        next_page = self.__current + 1
        if next_page >= len(self.spine_primary):
            raise IndexError

        self.page = next_page

    def get_page(self):
        return self.page

    def set_page(self, i):
        self.page = i

    def set_page_by_path(self, path):
        if path in self.spine_primary:
            i = self.spine_primary.index(path)
            self.set_page(i)

    def get_current_path(self):
        return self.spine_primary[self.__current]

    def get_current_id(self):
        path = self.get_current_path()
        return self.get_resource_id(path)

    def get_current(self):
        path = self.get_current_path()
        return self.get_resource_content(path)

    def get_current_mime(self):
        path = self.get_current_path()
        mime = self.get_resource_mime(path)

        # if mime == 'application/xhtml+xml':
        #     return 'text/html'

        return mime

    def get_current_with_epub_uris(self):
        path = self.get_current_path()
        content = self.get_resource_with_epub_uris(path)
        #content = bytes(python_html.unescape(str(content, encoding='utf8')),
        #                encoding='utf8')

        return content

    def get_pages_positions(self):
        return self.pages_positions

    def get_current_position(self):
        return self.pages_positions[self.__current]

    def get_next_position(self):
        if self.__current == len(self.spine_primary) - 1:
            return 100

        return self.pages_positions[self.__current + 1]

    def get_metadata(self, _id):
        return self.metadata.get(_id)

    def find_text(self, search_text):
        found_list = []
        found = False

        for path in self.spine_primary:
            res = self.get_resource_content(path)
            res_mime = self.get_resource_mime(path)
            res_elem = self._bytes_to_elem(res, res_mime)
            res_body = res_elem.xpath('//*[local-name() = "body"]')

            for body in res_body:
                body_text = ''
                for child in body.iter():
                    if child.text and not isinstance(child, etree._Comment):
                        body_text += child.text

                found = search_text.lower() in body_text.lower()

            found_list.append([path, found])

        return found_list

    # Internal functions #

    def _is_file(self, path):
        """
        Check if the given path is a file

        :return: A boolean representing if the given path is a file
        """
        if not GLib.file_test(path, GLib.FileTest.IS_REGULAR):
            return False

        return True

    def _open_zip_archive(self, zip_path):
        """
        Open a zip file from the given path

        :param zip_path: A string containing the path to the file
        :return: A zipfile.ZipFile object or None
        """
        epub_zip = None

        try:
            epub_zip = zipfile.ZipFile(zip_path,
                                       'r',
                                       compression=zipfile.ZIP_DEFLATED,
                                       allowZip64=True)
        except (zipfile.BadZipFile, zipfile.LargeZipFile):
            pass

        return epub_zip

    def _read_inner_zip_path(self, epub_zip, inner_path):
        """
        Read a file inside a zip object

        :param epub_zip: A zipfile.ZipFile object
        :param inner_path: A string representing a path
        :return: A python bytes string or None
        """
        try:
            path_bytes = epub_zip.read(inner_path)
        except KeyError:
            self._raise_resource_not_found(inner_path)

        return path_bytes

    def _has_epub_mime(self, epub_zip):
        """
        Check if the zip file contains a correct epub mimetype file

        :param epub_zip: A zipfile.ZipFile object
        :return: True or False
        """
        mimetype = None

        try:
            mimetype = self._read_inner_zip_path(epub_zip, 'mimetype')
        except BookError:
            pass

        if mimetype == b'application/epub+zip':
            return True

        return False

    def _read_opf_path(self, epub_zip):
        """
        Find the OPF file path

        :param epub_zip: A zipfile.ZipFile object
        :return: A string pointing to the OPF file inside the zip file or None
        """
        # <rootfiles>
        #   <rootfile full-path="OEBPS/content.opf"
        #       media-type="application/oebps-package+xml"/>
        opf_path = None
        xml_mime = 'application/xml'
        container_mime = 'META-INF/container.xml'
        container_bytes = self._read_inner_zip_path(epub_zip, container_mime)
        container_elem = self._bytes_to_elem(container_bytes, xml_mime)
        xpath_string = './/' + OASIS + 'rootfile[@media-type]'
        rootfile_list = container_elem.findall(xpath_string)

        for rootfile in rootfile_list:
            if rootfile.get('media-type') == 'application/oebps-package+xml':
                opf_path = rootfile.get('full-path')
                break

        return opf_path

    def _get_opf_metadata(self, opf_elem):
        """
        Get all metadata elements inside the OPF file

        :param opf_elem: A lxml.etree object
        :return: A dictionary containing the metadata
        """
        # <package … unique-identifier="pub-id">
        #     …
        #     <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
        #         <dc:identifier id="pub-id">urn:uuid:A1B0D67E</dc:identifier>
        #         <dc:title>Norwegian Wood</dc:title>
        #         <dc:language>en</dc:language>
        #         <meta property="dcterms:modified">2011-01-01T12:00:00Z</meta>
        #     </metadata>
        #     …
        # </package>
        metadata_elem = opf_elem.find(OPF + 'metadata')
        metadata = {}

        for child in metadata_elem:
            if not etree.iselement(child) or child.tag is etree.Comment:
                continue

            tag = child.tag[child.tag.rfind('}') + 1:]

            if child.prefix and child.prefix.lower() == 'dc':
                if self.metadata.get(tag, None):
                    metadata[tag].append(child.text)
                else:
                    metadata[tag] = [child.text]

        return metadata

    def _get_opf_resources(self, opf_path, opf_elem, epub_zip):
        """
        Get all relevant files inside an epub file, using the opf file as
        reference.

        :param opf_path: The original OPF file path
        :param opf_elem: A lxml.etree object
        :param epub_zip: A zipfile.ZipFile object
        :return: A tuple containing two dictionaries,
            the first one containing all epub resources by path {path: (id, …)}
            and the second containing all resources paths by id {id: path}
        """
        # manifest
        # TODO: Check OPS Core Media Types
        # MIME Media Type           Description
        # image/gif                    Used for raster graphics
        # image/jpeg                Used for raster graphics
        # image/png                 Used for raster graphics
        # image/svg+xml             Used for vector graphics
        # application/xhtml+xml     Used for OPS Content Documents
        # application/x-dtbook+xml  Used for OPS Content Documents
        # text/css                  Used for OPS CSS-subset style sheets
        # application/xml           Used for Out-Of-Line XML Islands
        # text/x-oeb1-document      Deprecated; OEBPS 1.0.1 and 1.2 Documents
        # text/x-oeb1-css           Deprecated; OEBPS 1.0.1 and 1.2 CSS
        # application/x-dtbncx+xml  The NCX
        #
        # Do not render img or object elements of unsupported media types,
        # in the absence of fallbacks.
        resources = {}
        resources_by_id = {}

        opf_dir_path = posixpath.dirname(opf_path)

        manifest_elem = opf_elem.find(OPF + 'manifest')
        for child in manifest_elem:
            if not etree.iselement(child) and child.tag != OPF + 'item':
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
            res_inner_path = Soup.URI.decode(child.get('href'))
            res_path = posixpath.join(opf_dir_path, res_inner_path)
            res_content = self._read_inner_zip_path(epub_zip, res_path)

            resources[res_path] = {
                'id': res_id,
                'content': res_content,
                'mimetype': res_type,
                'properties': res_props
            }
            resources_by_id[res_id] = res_path

        return resources, resources_by_id

    def _get_toc_path(self, opf_elem):
        """
        Gets the path of the resource that contains the TOC

        :param opf_elem: A lxml.etree object
        :return: A string containing the path of the TOC resource
        """
        # EPUB2
        # <spine toc="ncx">
        #   <itemref idref="intro" />
        #   <itemref idref="c1" />
        toc = ''

        spine_elem = opf_elem.find(OPF + 'spine')
        ncx_id = spine_elem.get('toc')

        if ncx_id:
            toc = self.resources_by_id[ncx_id]

        if toc or not self.resources:
            return toc

        for key in self.resources:
            resource_properties = self.resources[key]['properties']
            resource_mimetype = self.resources[key]['mimetype']
            if ('nav' in resource_properties
                and resource_mimetype == 'application/xhtml+xml'):
                resource_id = self.resources[key]['id']
                toc = self.resources_by_id[resource_id]
                break

        return toc

    def _get_opf_progression_direction(self, opf_elem):
        """
        Gets the direction of the epub file

        :param opf_elem: A lxml.etree object
        :return: A string with the direction of the document
        """
        spine_elem = opf_elem.find(OPF + 'spine')

        ppd = spine_elem.get('page-progression-direction')
        if ppd:
            direction = ppd
        else:
            direction = 'default'

        return direction

    def _get_opf_spine(self, opf_elem):
        """
        Gets the spine of the epub file

        :param opf_elem: A lxml.etree object
        :return list: A list of strings with all paths of the spine
        """
        spine_primary = []
        spine_auxiliary = []
        spine_elem = opf_elem.find(OPF + 'spine')

        for child in spine_elem:
            if not etree.iselement(child) and child.tag != OPF + 'itemref':
                continue

            res_id = child.get('idref')
            linear = child.get('linear', 'yes')

            mimetype = self.resources[self.resources_by_id[res_id]]['mimetype']
            if not self._is_ops_document(mimetype):
                pass

            if linear == 'yes':
                spine_primary.append(self.resources_by_id[res_id])
            else:
                spine_auxiliary.append(self.resources_by_id[res_id])

        print(spine_primary)
        print(spine_auxiliary)

        return spine_primary, spine_auxiliary

    def _get_opf_guide(self, opf_path, opf_elem):
        """
        Return a list guide

        :param opf_path: The original OPF file path
        :type opf_path: str
        :param opf_elem: The tree of the OPF file
        :type opf_elem: lxml.etree
        :return: A list with the guide information
        :rtype: list
        """
        guide = []
        opf_dir_path = posixpath.dirname(opf_path)
        guide_elem = opf_elem.find(OPF + 'guide')

        if guide_elem is not None:
            for child in guide_elem:
                if (not etree.iselement(child)
                    and child.tag != OPF + 'reference'):
                    continue

                ref_type = child.get('type')
                ref_title = child.get('title')
                ref_inner_path = Soup.URI.decode(child.get('href'))
                ref_href = posixpath.join(opf_dir_path, ref_inner_path)

                guide.append((ref_href, ref_title, ref_type))

        return guide

    def _get_opf_landmarks(self, opf_elem):
        # TODO: Implement landmarks
        landmarks = []
        if self.version == 3.0:
            pass

        return landmarks

    def _is_ops_document(self, mimetype):
        """
        Check if given mimetype is an OPS document

        :param mimetype: A string like 'application/xxx-xxx'
        """
        # TODO: Out-Of-Line XML Island (with required fallback.)
        if (mimetype == 'application/xhtml+xml'
            or mimetype == 'application/x-dtbook+xml'
            or mimetype == 'text/x-oeb1-document'):
            return True

        return False

    def _bytes_to_elem(self, content_bytes, mimetype):
        """ Convert from python bytes to lxml element

        :param content_bytes: Bytes containing an XML or HTML representation
        :param mimetype: A string containing the mimetype of the file
        :return: A lxml.etree._ElementTree object
        """
        if mimetype == 'application/xhtml+xml':
            parser = html.XHTMLParser(recover=True)
        else:
            parser = etree.XMLParser(recover=True)

        elem = html.fromstring(content_bytes, parser=parser).getroottree()

        return elem

    def _elem_to_bytes(self, elem, mimetype):
        encoding = elem.docinfo.encoding
        standalone = elem.docinfo.standalone

        content_bytes = etree.tostring(elem,
                                       xml_declaration=True,
                                       encoding=encoding,
                                       standalone=standalone)

        return content_bytes

    def _get_path_fragment(self, _path: str) -> list:
        path = ''
        fragment = ''

        if _path:
            soup_uri = Soup.URI.new(_path)
            path = soup_uri.get_path()[1:]
            fragment = soup_uri.get_fragment() or ''

        return [path, fragment]

    def _parse_ncx(self, toc_elem):
        toc_list = []

        navmap = toc_elem.find('{0}navMap'.format(DAISY))
        if navmap is None:
            return toc_list

        def get_children(item, children_list):
            title = item.find('{D}navLabel/{D}text'.format(D=DAISY)).text
            _path = item.find('{0}content'.format(DAISY)).get('src', '')
            path, fragment = self._get_path_fragment(_path)
            path = Soup.URI.decode(path)

            children_list.append({'title': title,
                                  'path': path,
                                  'fragment': fragment,
                                  'children': []})

            children = item.findall('{0}navPoint'.format(DAISY))
            if children:
                for child in children:
                    get_children(child, children_list[-1].get('children'))

        for nav_child in navmap.getchildren():
            get_children(nav_child, toc_list)

        return toc_list

    def _parse_nav(self, toc_elem):
        toc_list = []
        navs = toc_elem.findall('{X}body/{X}nav'.format(X=XHTML))

        def get_children(item, children_list):
            url = item.find('{0}a'.format(XHTML))
            title = url.text_content()
            _path = url.get('href')
            path, fragment = self._get_path_fragment(_path)
            path = Soup.URI.decode(path)

            children_list.append({'title': title,
                                  'path': path,
                                  'fragment': fragment,
                                  'children': []})

            child_ol = item.find('{0}ol'.format(XHTML))
            if child_ol is not None:
                li = child_ol.findall('{0}li'.format(XHTML))
                for child in li:
                    get_children(child, children_list[-1].get('children'))

        for nav in navs:
            if nav.get('{0}type'.format(EPUB)) == 'toc':
                nav_ol = nav.find('{0}ol'.format(XHTML))
                nav_li = nav_ol.findall('{0}li'.format(XHTML))
                for li_item in nav_li:
                    get_children(li_item, toc_list)

        return toc_list

    def _replace_uris(self, resource_path, content_bytes, mimetype):
        dirname = posixpath.dirname(resource_path)
        elem = self._bytes_to_elem(content_bytes, mimetype)

        def set_epub_uri(tag, attr, ns):
            if dirname:
                path_base = 'epub:///{0}/'.format(dirname)
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
                pre_ancestors = e.iterancestors('{*}pre')
                has_pre = False
                for pre_element in pre_ancestors:
                    has_pre = True
                    break

                if has_pre:
                    continue

                attr_content = e.get(attrname)
                if attr_content:
                    if attr_content.startswith('#'):
                        soup_base = Soup.URI.new('epub:///' + resource_path)

                    soup_uri = Soup.URI.new_with_base(soup_base, attr_content)
                    uri = soup_uri.to_string(False)
                    e.set(attrname, uri)

        set_epub_uri('link', 'href', None)
        set_epub_uri('img', 'src', None)
        set_epub_uri('image', 'href', XLINK)
        set_epub_uri('a', 'href', None)
        set_epub_uri('content', 'src', None)

        return self._elem_to_bytes(elem, mimetype)

    def _calculate_pages_positions(self):
        pages_sizes = []
        total_size = 0
        pages_positions = []

        for page_path in self.spine_primary:
            page_res = self.get_resource_content(page_path)
            page_size = sys.getsizeof(page_res)
            total_size += page_size
            pages_sizes.append(page_size)

        accumulated_sizes = 0
        for page_size in pages_sizes:
            percent = accumulated_sizes / total_size * 100
            pages_positions.append(percent)
            accumulated_sizes += page_size

        return pages_positions
