#! /usr/bin/env python3

import os

try:
    from setuptools import find_packages, setup
except AttributeError:
    from setuptools import find_packages, setup

NAME = 'OASYS1-APS-Extensions'
VERSION = '0.0.6'
ISRELEASED = False

DESCRIPTION = 'ShadowOui/SRW extensions for the APS'
README_FILE = os.path.join(os.path.dirname(__file__), 'README.txt')
LONG_DESCRIPTION = open(README_FILE).read()
AUTHOR = 'Luca Rebuffi'
AUTHOR_EMAIL = 'lrebuffi@anl.gov'
URL = 'https://github.com/oasys-aps-kit/OASYS1-APS-Extensions'
DOWNLOAD_URL = 'https://github.com/oasys-aps-kit/OASYS1-APS-Extensions'
LICENSE = 'GPLv3'

KEYWORDS = (
    'raytracing',
    'simulator',
    'oasys1',
)

CLASSIFIERS = (
    'Development Status :: 4 - Beta',
    'Environment :: X11 Applications :: Qt',
    'Environment :: Console',
    'Environment :: Plugins',
    'Programming Language :: Python :: 3',
    'Intended Audience :: Science/Research',
)

SETUP_REQUIRES = (
    'setuptools',
)

INSTALL_REQUIRES = (
    'setuptools',
)

PACKAGES = find_packages(exclude=('*.tests', '*.tests.*', 'tests.*', 'tests'))

PACKAGE_DATA = {
    "orangecontrib.aps.oasys.widgets.extension":["icons/*.png", "icons/*.jpg", "misc/*.png"],
    "orangecontrib.aps.shadow.widgets.extension":["icons/*.png", "icons/*.jpg", "misc/*.png"],
    "orangecontrib.aps.srw.widgets.extension":["icons/*.png", "icons/*.jpg", "misc/*.png"],
}

NAMESPACE_PACAKGES = ["orangecontrib",
                      "orangecontrib.aps",
                      "orangecontrib.aps.oasys",
                      "orangecontrib.aps.shadow",
                      "orangecontrib.aps.srw",
                      "orangecontrib.aps.oasys.widgets",
                      "orangecontrib.aps.shadow.widgets",
                      "orangecontrib.aps.srw.widgets",
                      ]

ENTRY_POINTS = {
    'oasys.addons' : ("Oasys APS Extension = orangecontrib.aps.oasys",
                      "Shadow APS Extension = orangecontrib.aps.shadow",
                      "SRW APS Extension = orangecontrib.aps.srw",
                      ),
    'oasys.widgets' : (
        "Oasys APS Extension = orangecontrib.aps.oasys.widgets.extension",
        "Shadow APS Extension = orangecontrib.aps.shadow.widgets.extension",
        "SRW APS Extension = orangecontrib.aps.srw.widgets.extension",
    ),
}

if __name__ == '__main__':
    try:
        import PyMca5, PyQt4

        raise NotImplementedError("This version of APS ShadowOui doesn't work with Oasys1 beta.\nPlease install OASYS1 final release: http://www.elettra.eu/oasys.html")
    except:
        setup(
              name = NAME,
              version = VERSION,
              description = DESCRIPTION,
              long_description = LONG_DESCRIPTION,
              author = AUTHOR,
              author_email = AUTHOR_EMAIL,
              url = URL,
              download_url = DOWNLOAD_URL,
              license = LICENSE,
              keywords = KEYWORDS,
              classifiers = CLASSIFIERS,
              packages = PACKAGES,
              package_data = PACKAGE_DATA,
              #          py_modules = PY_MODULES,
              setup_requires = SETUP_REQUIRES,
              install_requires = INSTALL_REQUIRES,
              #extras_require = EXTRAS_REQUIRE,
              #dependency_links = DEPENDENCY_LINKS,
              entry_points = ENTRY_POINTS,
              namespace_packages=NAMESPACE_PACAKGES,
              include_package_data = True,
              zip_safe = False,
              )
