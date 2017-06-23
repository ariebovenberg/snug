from setuptools import setup, find_packages


setup(
    name='snug',
    version='0.1.0',
    description='Wrap REST APIs to fit nicely into your python code',
    author='Arie Bovenberg',
    url='https://github.com/ariebovenberg/snug',
    packages=find_packages(exclude=('tests', 'docs', 'examples'))
)
