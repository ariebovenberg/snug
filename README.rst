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


**Snug** is a compact toolkit for wrapping web APIs.
Architecture agnostic, pluggable, and interchangeably sync/async.
Write API interactions as regular python code.

Quickstart
----------

1. API interactions ("queries") are request/response generators:

   .. code-block:: python

    import json
    import snug

    def repo(name: str, owner: str) -> snug.Query[dict]:
        """a repo lookup by owner and name"""
        request = snug.GET(f'https://api.github.com/repos/{owner}/{name}')
        response = yield request
        return json.loads(response.data)

2. Queries can be executed:

   .. code-block:: python

    >>> query = repo('Hello-World', owner='octocat')
    >>> snug.execute(query)
    {"description": "My first repository on Github!", ...}

3. That's it


Installation
------------

There are no required dependencies on python 3.5+. Installation is easy as:

.. code-block:: bash

   pip install snug

Although snug includes basic sync and async HTTP clients,
you may wish to install `requests <http://docs.python-requests.org/>`_
and/or `aiohttp <http://aiohttp.readthedocs.io/>`_.

.. code-block:: bash

   pip install requests
   pip install aiohttp

Features
--------

1. *Simplicity*. If you understand generators, you understand queries.
   Customizing a query requires no special glue-code.
   For example: add validation logic, or use any serialization method:

   .. code-block:: python

     from my_types import User, UserSchema

     def user(name: str) -> snug.Query[User]:
         """lookup a user by their username"""
         if len(name) == 0:
             raise ValueError('username must have >0 characters')
         request = snug.GET(f'https://api.github.com/users/{name}')
         response = yield request
         return UserSchema().load(json.loads(response.data))

2. *Async out-of-the-box*. The same query can also be executed asynchronously:

   .. code-block:: python

      query = repo('Hello-World', owner='octocat')
      repo = await snug.execute_async(query)

3. *Pluggable clients*. Queries are fully agnostic of the HTTP client.
   For example, to use ``requests`` instead of the built-in ``urllib``:

   .. code-block:: python

      >>> import requests
      >>> execute = snug.executor(client=requests.Session())
      >>> execute(repo('Hello-World', owner='octocat'))
      {"description": "My first repository on Github!", ...}

4. *Testable*. Since queries are just generators, we can run them
   just fine without touching the network.
   No need for complex mocks or monkeypatching.

   .. code-block:: python

      >>> query = iter(epo('Hello-World', owner='octocat'))
      >>> next(query).url.endswith('/repos/octocat/Hello-World')
      True
      >>> query.send(snug.Response(200, ...))
      StopIteration({"description": "My first repository on Github!", ...})

5. *Swappable authentication*. Different credentials can be used to execute
   the same query.

   .. code-block:: python

      def follow(name: str) -> snug.Query[bool]:
          """follow another user"""
          req = snug.PUT('https://api.github.com/user/following/{name}')
          return (yield req).status_code == 204

      exec_as_me = snug.executor(auth=('me', 'password'))
      exec_as_bob = snug.executor(auth=('bob', 'password'))

      exec_as_me(follow('octocat'))
      exec_as_bob(follow('octocat'))

6. *Related queries*. Use class-based queries to create a chained API for related objects:

   .. code-block:: python

      class repo(snug.Query[dict]):
          """a repo lookup by owner and name"""
          def __init__(self, name, owner):
              ...

          def __iter__(self):
              ...  # query for the repo itself

          def issue(self, num: int) -> snug.Query[dict]:
              """retrieve an issue in this repository by its number"""
              req = snug.GET(f'/repos/{self.owner}/{self.name}/issues/{num}')
              return json.loads((yield req).data)

      # the `repo` query works as before
      hello_world_repo = repo('Hello-World', owner='octocat')
      # ...but now we can make a related query
      issue_lookup = hello_world_repo.issue(348)
      snug.execute(issue_lookup)
      # {"title": "Testing comments", ...}

7. *Composable*. If you're comfortable with high-order functions and decorators,
   make use of `gentools <http://gentools.readthedocs.io/>`_ to create generators
   and apply functions to a generator's
   ``yield``, ``send``, and ``return`` values.

   .. code-block:: python

      from gentools import (map_return, map_yield, map_send,
                            compose, oneyield)

      class Repository:
          ...

      def my_repo_loader(...):
          ...  # e.g. create a nice `Repository` object

      def my_error_checker(...):
          ...  # e.g. raise descritive errors on HTTP 4xx responses

      def my_request_preparer(...):
          ...  # e.g. add headers, url prefix, etc

      basic_interaction = compose(map_send(my_error_checker),
                                  map_yield(my_request_preparer))

      @map_return(my_repo_loader)
      @basic_interaction
      @oneyield
      def repo(owner: str, name: str) -> snug.Query[Repository]:
          """get a repo by owner and name"""
          return snug.GET(f'/repos/{owner}/{name}')

      @basic_interaction
      def follow(name: str) -> snug.Query[bool]:
          """follow another user"""
          response = yield snug.PUT(f'/user/following/{name}')
          return response.status_code == 204

   Alternatively, use a class-based approach:

   .. code-block:: python

      class BaseQuery(snug.Query):
          """base github query"""

          def prepare(self, request):
              ...  # e.g. add headers, url prefix, etc

          def __iter__(self):
              return parse_result((yield self.prepare(self.request)))

          def parse_result(self, result):
              ...  # e.g. error checking


      class repo(BaseQuery):
          """get a repo by owner and name"""
          def __init__(self, name, owner):
              self.request = snug.GET(f'/repos/{owner}/{name}')

          def parse_result(self, result):
              result = super().parse_result(result)
              return my_repo_loader(result.data)


      class follow(BaseQuery):
          """follow another user"""
          def __init__(self, name):
              self.request = snug.PUT(f'/user/following/{name}')

          def parse_result(self, result):
              result = super().parse_result(result)
              return result.status_code == 204


Check the ``examples/`` directory for some samples.
