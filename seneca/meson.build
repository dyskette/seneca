pkgdatadir = join_paths(get_option('prefix'), get_option('datadir'), meson.project_name())
moduledir = join_paths(pkgdatadir, 'seneca')

seneca_sources = [
  '__init__.py',
  '__main__.py',
  'gi_composites.py',
  'application.py',
  'window.py',
  'dialogs.py',
  'book.py',
  'book_error.py',
  'epub.py',
  'font.py',
  'settings.py',
  'toc.py',
  'pagination.py'
]

install_data(seneca_sources, install_dir: moduledir)
