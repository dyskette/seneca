#!/usr/bin/env python3
#
# python3 setup.py install --user
#
# python3 setup.py install --single-version-externally-managed --root / --prefix /usr

import os
import setuptools
from seneca import VERSION
import compile_resources

compile_resources.build()

long_description = ''
if os.path.isfile('README.rst'):
    long_description = open('README.rst', 'r').read()
elif os.path.isfile("README.md"):
    long_description = open('README.md', 'r').read()

setuptools.setup(
    name='seneca',
    version=VERSION,

    description='A cute epub reader',
    long_description=long_description,
    keywords='epub viewer gnome',

    url='https://github.com/dyskette/seneca',

    author='Eddy Castillo',
    author_email='dyskette@gmail.com',

    license='GPL-3',
    classifiers=[
        'Development Status :: 2 - Pre-Alpha',

        'Environment :: X11 Applications :: Gnome',
        'Intended Audience :: End Users/Desktop',
        'Topic :: Desktop Environment :: Gnome',

        'License :: OSI Approved :: GNU General Public License v3 (GPLv3)',

        'Operating System :: POSIX :: Linux',

        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7'
    ],

    packages=['seneca'],

    package_data={
        'seneca': ['seneca.gresource'],
    },

    # This requires the option --single-version-externally-managed
    data_files=[
        ('share/applications', ['data/com.github.dyskette.seneca.desktop']),
        ('share/icons/hicolor/scalable/apps', ['data/com.github.dyskette.seneca.svg'])
    ],

    install_requires=['lxml'],

    python_requires='>=3',

    entry_points={
        'console_scripts': [
            'com.github.dyskette.seneca = seneca.__main__:main',
        ],
    }
)
