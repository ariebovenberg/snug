import os.path
import re
from setuptools import setup, find_packages


def read(fname):
    path = os.path.join(os.path.dirname(__file__), fname)
    with open(path, 'r') as rfile:
        return rfile.read()


import snug.__about__ as metadata


setup(
    name='snug',
    version=metadata.__version__,
    description=metadata.__description__,
    license='MIT',
    long_description=read('README.rst') + '\n\n' + read('HISTORY.rst'),
    url='https://github.com/ariebovenberg/snug',

    author=metadata.__author__,
    author_email='a.c.bovenberg@gmail.com',

    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',

        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
    ],
    install_requires=[
        'typing>=3.6.2;python_version<"3.5"'
    ],
    keywords=['api-wrapper', 'http', 'generators', 'async',
              'graphql', 'rest', 'rpc'],
    python_requires='>=3.4',
    packages=find_packages(exclude=('examples', 'tests', 'docs')),
)
