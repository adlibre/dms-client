"""
Compile script for py2exe.

In order to compile this you need to install py2exe.
From here: http://sourceforge.net/projects/py2exe/files/py2exe/

Compile environment must be win32 (Win XP, Win Server and so on...)

You must follow instructions from here: http://www.py2exe.org/index.cgi/Tutorial

In short, you must run:

# python compile_w32.py py2exe

It will produce 2 folders /build/ and /dist/

/dist/ is your distributable version.
Rename it and use like a program distribution.
"""

from distutils.core import setup
import py2exe

setup(console=['dms_client.py']) 
