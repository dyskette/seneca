# Seneca

Seneca is a cute epub reader. This is a work in progress, beware of bugs.

## Installation

Download the files, extract and then run the following inside the folder:

```
mkdir builddir
cd builddir
meson ..
ninja
sudo ninja install
```

To run:

```
seneca
```

## Requirements

For installation:
- meson
- glib-compile-schemas

For running:
- Python 3
- GTK+ 3
- WebKit2
- lxml2

## License

This software is under the GPLv3. See LICENSE.
