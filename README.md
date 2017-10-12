# Seneca (in development)

Seneca is an epub reader made to fit in GNOME.

## Screenshot

![](data/screenshots/screenshot1.png)
![](data/screenshots/screenshot2.png)

## Installation

To download:
```
git clone git@github.com:dyskette/seneca.git
cd seneca
```

To build and install, seneca uses [meson](http://mesonbuild.com) with
[ninja](https://ninja-build.org). Run the following commands:
```
meson builddir
ninja -C builddir
sudo ninja -C builddir install
```

## Requirements

For installation:
- gcc
- python3
- pygobject-3.0
- webkit2gtk-web-extension-4.0
- meson
- glib-compile-schemas

For running:
- python3
- python3-gobject
- python3-lxml
- webkit2gtk

## License

This software is under the GPLv3. See the [COPYING](COPYING) file.
