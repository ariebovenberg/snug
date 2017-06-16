from setuptools import setup, find_packages


setup(
    name='omgorm',
    version='0.1.0',
    description='an ORM toolkit for wrapping REST APIs',
    author='Arie Bovenberg',
    url='https://github.com/ariebovenberg/omgorm',
    packages=find_packages(exclude=('tests', 'docs', 'examples'))
)
