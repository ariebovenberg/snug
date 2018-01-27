import os.path
from setuptools import setup, find_packages


def read_local_file(fname):
    path = os.path.join(os.path.dirname(__file__), fname)
    with open(path, 'r') as rfile:
        return rfile.read()


metadata = {}
exec(read_local_file('snug/__about__.py'), metadata)
readme = read_local_file('README.rst')
history = read_local_file('HISTORY.rst')


setup(
    name='snug',
    version=metadata['__version__'],
    description=metadata['__description__'],
    license='MIT',
    long_description=readme + '\n\n' + history,
    url='https://github.com/ariebovenberg/snug',

    author=metadata['__author__'],
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
    keywords=['api', 'wrapper', 'rest', 'http'],
    python_requires='>=3.4',
    packages=find_packages(exclude=('tests', 'docs', 'examples'))
)
