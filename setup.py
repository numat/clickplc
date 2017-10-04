from platform import python_version
from setuptools import setup

if python_version() < '3.5':
    raise ImportError("This module requires Python >=3.5")

setup(
    name="clickplc",
    version="0.1.1",
    description="Python driver for Koyo Ethernet ClickPLCs.",
    url="http://github.com/numat/clickplc/",
    author="Patrick Fuller",
    author_email="pat@numat-tech.com",
    packages=['clickplc'],
    install_requires=[
        'pymodbus'
    ],
    dependency_links=[
        'git+https://github.com/riptideio/pymodbus.git@python3#egg=pymodbus-1.2.1'  # noqa
    ],
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
