from platform import python_version
from setuptools import setup

if python_version() < '3.5':
    raise ImportError("This module requires Python >=3.5")

if python_version() > '3.7':
    raise ImportError("This module requires Python <3.7")

setup(
    name="clickplc",
    version="0.1.13",
    description="Python driver for Koyo Ethernet ClickPLCs.",
    url="http://github.com/numat/clickplc/",
    author="Patrick Fuller",
    author_email="pat@numat-tech.com",
    packages=['clickplc'],
    entry_points={
        'console_scripts': [('clickplc = clickplc:command_line')]
    },
    install_requires=[
        'pymodbus>=2.0.0',
        'twisted'  # Needed due to quirk in pymodbus import structure (#338)
    ],
    license='GPLv2',
    classifiers=[
        'License :: OSI Approved :: GNU General Public License v2 (GPLv2)',
        'Development Status :: 4 - Beta',
        'Natural Language :: English',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Topic :: Scientific/Engineering :: Human Machine Interfaces'
    ]
)
