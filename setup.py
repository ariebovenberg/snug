import os.path
import re
from setuptools import setup


def read(fname):
    path = os.path.join(os.path.dirname(__file__), fname)
    with open(path, 'r') as rfile:
        return rfile.read()


def find_version(path):
    version_file = read(path)
    version_match = re.search(r"^__version__ = ['\"]([^'\"]*)['\"]",
                              version_file, re.M)
    if version_match:
        return version_match.group(1)
    raise RuntimeError("Unable to find version string.")


setup(
    name='snug',
    version=find_version('snug.py'),
    description='Write reusable web API interactions',
    license='MIT',
    long_description=read('README.rst') + '\n\n' + read('HISTORY.rst'),
    url='https://github.com/ariebovenberg/snug',

    author='Arie Bovenberg',
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
    py_modules=('snug',),
)
