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

def make_things():
    execute_this([resource_cmd, resource_file], resource_dir)
    execute_this(['mv', 'data/seneca.gresource', 'seneca'])

if __name__ == '__main__':
    make_things()
    from seneca import __main__
    __main__.main()
