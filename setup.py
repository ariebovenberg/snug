from pathlib import Path
from setuptools import setup, find_packages

local_path = Path(__file__).parent.joinpath

version_namespace = {}
exec(local_path('snug/__info__.py').open().read(), version_namespace)

readme = local_path('README.rst').open().read()
history = local_path('HISTORY.rst').open().read()


setup(
    name='snug',
    version=version_namespace['__version__'],
    description='Wrap REST APIs to fit nicely into your python code',
    license='MIT',
    long_description=readme + '\n\n' + history,
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
