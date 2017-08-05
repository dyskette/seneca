#!/usr/bin/env python3

import os
import sys
import subprocess

resource_file = 'softbook.gresource.xml'
resource_cmd = 'glib-compile-resources'
resource_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')

def execute_this(cmd_list, path=None):
    try:
        subprocess.check_call(cmd_list, cwd=path)
    except Exception as e:
        print('Exception!! => ', e)

def make_things():
    execute_this([resource_cmd, resource_file], resource_dir)
    execute_this(['cp', 'data/softbook.gresource', 'softbook'])

def main():
    make_things()

    import gi
    from gi.repository import Gio

    filename = 'data/softbook.gresource'
    resource = Gio.Resource.load(filename)
    Gio.Resource._register(resource)

    from softbook import application
    app = application.Application()

    try:
        ret = app.run(sys.argv)
    except SystemExit as e:
        ret = e.code

    sys.exit(ret)

if __name__ == '__main__':
    main()
