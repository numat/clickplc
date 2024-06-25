"""Python driver for AutomationDirect (formerly Koyo) Ethernet ClickPLCs."""

from setuptools import setup

with open('README.md') as in_file:
    long_description = in_file.read()

setup(
    name='clickplc',
    version='0.9.0',
    description="Python driver for Koyo Ethernet ClickPLCs.",
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://github.com/alexrudd2/clickplc/',
    author='Patrick Fuller',
    author_email='pat@numat-tech.com',
    maintainer='Alex Ruddick',
    maintainer_email='alex@ruddick.tech',
    packages=['clickplc'],
    entry_points={
        'console_scripts': [('clickplc = clickplc:command_line')]
    },
    install_requires=[
        'pymodbus>=2.4.0; python_version == "3.8"',
        'pymodbus>=2.4.0; python_version == "3.9"',
        'pymodbus>=3.0.2,<3.7.0; python_version >= "3.10"',
    ],
    extras_require={
        'test': [
            'pytest',
            'pytest-asyncio>=0.23.7,<=0.23.9',
            'pytest-cov',
            'pytest-xdist',
            'mypy==1.10.1',
            'ruff==0.4.7',
        ],
    },
    license='GPLv2',
    classifiers=[
        'License :: OSI Approved :: GNU General Public License v2 (GPLv2)',
        'Development Status :: 4 - Beta',
        'Natural Language :: English',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Programming Language :: Python :: 3.12',
        'Topic :: Scientific/Engineering :: Human Machine Interfaces'
    ]
)
