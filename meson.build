project('seneca', 'c',
  version: '0.0.1',
  meson_version: '>= 0.40.0',
)
i18n = import('i18n')

subdir('bin')
subdir('data')
subdir('seneca')
subdir('webextension')
subdir('po')
meson.add_install_script('build-aux/meson/postinstall.py')
