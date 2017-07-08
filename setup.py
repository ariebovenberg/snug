import os.path
from setuptools import setup, find_packages


thisdir = os.path.dirname(__file__)


with open(os.path.join(thisdir, 'README.rst')) as rfile:
    readme = rfile.read()


setup(
    name='snug',
    version='0.1.0',
    description='Wrap REST APIs to fit nicely into your python code',
    license='MIT',
    long_description=readme,
    url='https://github.com/ariebovenberg/snug',

    author='Arie Bovenberg',
    author_email='a.c.bovenberg@gmail.com',

    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',

        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
    ],
    keywords=['api', 'wrapper', 'rest', 'orm'],
    install_requires=[
        'requests>=2.13.0,<3',
        'typing',
    ],
    python_requires='>=3.4',
    packages=find_packages(exclude=('tests', 'docs', 'examples'))
)
