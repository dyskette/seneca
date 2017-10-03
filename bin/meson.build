pkgdatadir = join_paths(get_option('prefix'), get_option('datadir'), meson.project_name())
extensiondir = join_paths(get_option('prefix'), get_option('libdir'), meson.project_name(), 'webkitextension')

python3 = import('python3')

conf = configuration_data()
conf.set('PYTHON', python3.find_python().path())
conf.set('VERSION', meson.project_version())
conf.set('localedir', join_paths(get_option('prefix'), get_option('localedir')))
conf.set('pkgdatadir', pkgdatadir)
conf.set('extensiondir', extensiondir)

configure_file(
  input: 'seneca.in',
  output: 'seneca',
  configuration: conf,
  install: true,
  install_dir: get_option('bindir')
)
