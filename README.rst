Snug
====

.. image:: https://img.shields.io/pypi/v/snug.svg
    :target: https://pypi.python.org/pypi/snug

.. image:: https://img.shields.io/pypi/l/snug.svg
    :target: https://pypi.python.org/pypi/snug

.. image:: https://img.shields.io/pypi/pyversions/snug.svg
    :target: https://pypi.python.org/pypi/snug

.. image:: https://travis-ci.org/ariebovenberg/snug.svg?branch=master
    :target: https://travis-ci.org/ariebovenberg/snug

.. image:: https://coveralls.io/repos/github/ariebovenberg/snug/badge.svg?branch=master
    :target: https://coveralls.io/github/ariebovenberg/snug?branch=master

.. image:: https://readthedocs.org/projects/snug/badge/?version=latest
    :target: http://snug.readthedocs.io/en/latest/?badge=latest
    :alt: Documentation Status

.. image:: https://api.codeclimate.com/v1/badges/00312aa548eb87fe11b4/maintainability
   :target: https://codeclimate.com/github/ariebovenberg/snug/maintainability
   :alt: Maintainability


Wrap web APIs to fit nicely into your python code For python 3.5+.

Quickstart
----------

.. code-block:: python

   import json
   import snug

   @snug.querytype()
   def repo(name: str, owner: str):
      """a repo lookup by owner and name"""
      request = snug.http.GET(f'https://api.github.com/repos/{owner}/{name}')
      response = yield request
      return json.loads(response.data)

  exec = snug.http.simple_exec()

Check the ``examples/`` directory for some samples.
