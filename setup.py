
from __future__ import print_function
from setuptools import setup

import weighted

setup(
    name='wquantiles',
    version=weighted.__version__,
    url='http://github.com/nudomarinero/wquantiles/',
    license='MIT',
    author='Jose Sabater',
    tests_require=['pytest'],
    install_requires=['numpy'],
    author_email='jsm@iaa.es',
    description='Weighted quantiles, including weighted median, based on numpy',
    py_modules=['weighted'],
    )