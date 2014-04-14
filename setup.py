from __future__ import print_function
from setuptools import setup, Command
import os

import weighted


description = 'Weighted quantiles, including weighted median, based on numpy'
long_description = description
if os.path.exists('README.md'):
    with open('README.md') as f:
        long_description=f.read()


class PyTest(Command):
    user_options = []
    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def run(self):
        import sys,subprocess
        errno = subprocess.call([sys.executable, 'runtests.py'])
        raise SystemExit(errno)


setup(
    name='wquantiles',
    version=weighted.__version__,
    url='http://github.com/nudomarinero/wquantiles/',
    license='MIT License',
    author='Jose Sabater',
    tests_require=['pytest'],
    install_requires=['numpy'],
    author_email='jsm@iaa.es',
    description=description,
    long_description=long_description,
    platforms='any',
    classifiers = [
        'Programming Language :: Python',
        'Development Status :: 4 - Beta',
        'Natural Language :: English',
        'Environment :: Web Environment',
        'Intended Audience :: Science/Research',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Topic :: Scientific/Engineering :: Mathematics',
        'Topic :: Software Development :: Libraries :: Python Modules',
        ],
    py_modules=['weighted'],
    test_suite='test',
    cmdclass = {'test': PyTest},
    )