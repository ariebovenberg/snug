import os.path

from setuptools import find_packages, setup


def read(fname):
    path = os.path.join(os.path.dirname(__file__), fname)
    with open(path, "r") as rfile:
        return rfile.read()


metadata = {}
exec(read("snug/__about__.py"), metadata)


setup(
    name="snug",
    version=metadata["__version__"],
    description=metadata["__description__"],
    license="MIT",
    long_description=read("README.rst") + "\n\n" + read("HISTORY.rst"),
    url="https://github.com/ariebovenberg/snug",
    author=metadata["__author__"],
    author_email="a.c.bovenberg@gmail.com",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
    ],
    install_requires=[
        'typing>=3.6.6; python_version<"3.5"',
    ],
    extras_require={
        "aiohttp": ["aiohttp>=3.4.4,<3.7.0"],
        "requests": ["requests>=2.20,<2.23"],
    },
    keywords=[
        "api-wrapper",
        "http",
        "generators",
        "async",
        "graphql",
        "rest",
        "rpc",
    ],
    python_requires=">=3.5.2",
    packages=find_packages(exclude=("examples", "tests", "docs", "tutorial")),
)
