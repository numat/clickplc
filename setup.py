from platform import python_version
from setuptools import setup

if python_version() < '3.5':
    raise ImportError("This module requires Python >=3.5")

setup(
    name="clickplc",
    version="0.1.4",
    description="Python driver for Koyo Ethernet ClickPLCs.",
    url="http://github.com/numat/clickplc/",
    author="Patrick Fuller",
    author_email="pat@numat-tech.com",
    packages=['clickplc'],
    entry_points={
        'console_scripts': [('clickplc = clickplc:command_line')]
    },
    license='GPLv2',
    classifiers=[
        'License :: OSI Approved :: GNU General Public License v2 (GPLv2)',
        'Development Status :: 4 - Beta',
        'Natural Language :: English',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3.5',
        'Topic :: Scientific/Engineering :: Human Machine Interfaces'
    ]
)
