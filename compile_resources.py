#!/usr/bin/env python3

import os
import sys
import subprocess

resource_file = 'seneca.gresource.xml'
resource_cmd = 'glib-compile-resources'
resource_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')

def execute_this(cmd_list, path=None):
    try:
        subprocess.check_call(cmd_list, cwd=path)
    except Exception as e:
        print('Exception!! => ', e)

desktop_in = os.path.join('data', 'com.github.dyskette.Seneca.desktop.in')
desktop_out = os.path.join('data', 'com.github.dyskette.Seneca.desktop')
gresource_bin = os.path.join('data', 'seneca.gresource')

def build():
    execute_this([resource_cmd, resource_file], resource_dir)
    execute_this(['mv', gresource_bin, 'seneca'])
    execute_this(['cp', desktop_in, desktop_out])

if __name__ == '__main__':
    build()
