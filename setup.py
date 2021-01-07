#!/usr/bin/env python
# -*- coding: utf-8 -*-


'''setup.py: setuptools control.'''


import re
from setuptools import setup
from os import path

here = path.abspath(path.dirname(__file__))
with open(path.join(here, 'README.md'), 'r') as f:
    long_description = f.read()

version = "0.3.3"

setup(
    name='aws-ssm-copy',
    packages=['aws_ssm_copy'],
    entry_points={
        'console_scripts': ['aws-ssm-copy = aws_ssm_copy:main']
    },
    version=version,
    description='Copy AWS Parameter Store parameters',
    long_description=long_description,
    long_description_content_type="text/markdown",
    include_package_data=True,
    zip_safe=False,
    platforms='any',
    install_requires=['boto3' ],
    author='Mark van Holsteijn',
    author_email='markvanholsteijn@binx.io',
    url='https://github.com/binxio/aws-ssm-copy',
)
