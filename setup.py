#!/usr/bin/env python
# -*- coding: utf-8 -*-
#

from os.path import dirname, join
from setuptools import (
    find_packages,
    setup,
)

try: # for pip >= 10
    from pip._internal.req import parse_requirements
except ImportError: # for pip <= 9.0.3
    from pip.req import parse_requirements

try:
    req = [str(ir.req) for ir in parse_requirements("requirements.txt", session=False)]
except:
    req = [str(ir.requirement) for ir in parse_requirements("requirements.txt", session=False)]

with open(join(dirname(__file__), 'funcat/VERSION.txt'), 'rb') as f:
    version = f.read().decode('ascii').strip()

setup(
    name='funcat3',
    version=version,
    long_description='Using very simple code to compute indicator of stock and crytocurrency. Make quantify easier to everyone. Funcat has transplanted the indicator formulas of THS, Tongdaxin, Wenhua Finance, and other platforms into Python. It is suitable for quantitative analysis and trading of stocks, futures, contracts, and cryptocurrencies.',
    long_description_content_type="text/x-rst",
    packages=find_packages(exclude=[]),
    author='Guanjun',
    url='https://github.com/mapicccy/funcat',
    author_email='mapicccy@gmail.com',
    license='Apache License v2',
    package_data={'': ['*.*']},
    install_requires=req,
    zip_safe=False,
    classifiers=[
        'Programming Language :: Python',
        'Operating System :: Microsoft :: Windows',
        'Operating System :: Unix',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
    ],
)
