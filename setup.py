#!/usr/bin/env python

from setuptools import setup

from dms_client import __version__


setup(name='dms_client',
    version=__version__,
    long_description=open('README.md').read(),
    url='https://github.com/adlibre/dms-client',
    packages=[],
    scripts=['dms_client.py'],
    package_data={
            'dms_client': [
                'LICENSE',
                'README.md',
                '__init__.py',
                'dms_client.py',
            ],
        },
    data_files=[
        ('dms_client', ['dms_client.cfg'])
        ],
    install_requires=[
            # Python :)
        ],
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Topic :: Utilities",
        "License :: OSI Approved :: BSD License",
        ],
)


