pkgdatadir = join_paths(get_option('prefix'), get_option('datadir'), meson.project_name())
extensiondir = join_paths(get_option('libdir'), meson.project_name(), 'webkitextension')

webkitextension = dependency('webkit2gtk-web-extension-4.0')
pygobject = dependency('pygobject-3.0')
python3 = dependency('python3')

shared_library('pythonloader',
               'pythonloader.c',
               dependencies: [webkitextension, pygobject, python3],
               install: true,
               install_dir: extensiondir)

conf = configuration_data()
conf.set('pkgdatadir', pkgdatadir)

configure_file(
  input: 'extension.py.in',
  output: 'extension.py',
  configuration: conf,
  install_dir: extensiondir
)
