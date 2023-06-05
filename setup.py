"""Python driver for AutomationDirect (formerly Koyo) Ethernet ClickPLCs."""

from setuptools import setup

with open('README.md') as in_file:
    long_description = in_file.read()

setup(
    name='clickplc',
    version='0.7.0',
    description="Python driver for Koyo Ethernet ClickPLCs.",
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='http://github.com/numat/clickplc/',
    author='Patrick Fuller',
    author_email='pat@numat-tech.com',
    packages=['clickplc'],
    entry_points={
        'console_scripts': [('clickplc = clickplc:command_line')]
    },
    install_requires=[
        'pymodbus>=3.3.1,<4; python_version == "3.7"',
        'pymodbus>=2.4.0; python_version == "3.8"',
        'pymodbus>=2.4.0; python_version == "3.9"',
        'pymodbus>=3.0.2,<3.4.0; python_version >= "3.10"',
    ],
    extras_require={
        'test': [
            'pytest',
            'pytest-cov',
            'pytest-asyncio',
            'mypy==1.3.0',
            'ruff==0.0.270',
        ],
    },
    license='GPLv2',
    classifiers=[
        'License :: OSI Approved :: GNU General Public License v2 (GPLv2)',
        'Development Status :: 4 - Beta',
        'Natural Language :: English',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Topic :: Scientific/Engineering :: Human Machine Interfaces'
    ]
)
