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

* Architecture agnostic (REST, RPC, GraphQL, ...)
* Swappable HTTP clients (urllib, requests, aiohttp, ...)
* Interchangeably sync/async

Quickstart
----------

1. API interactions ("queries") are request/response generators:

   .. code-block:: python

    import json
    import snug

    def repo(name, owner):
        """a repo lookup by owner and name"""
        request = snug.GET(f'https://api.github.com/repos/{owner}/{name}')
        response = yield request
        return json.loads(response.content)

2. Queries can be executed:

   .. code-block:: python

    >>> query = repo('Hello-World', owner='octocat')
    >>> snug.execute(query)
    {"description": "My first repository on Github!", ...}

3. That's it


Why another library?
--------------------

There are plenty of tools for wrapping web APIs.
However, these generally make far-reaching design decisions for you,
making it awkward to bend it to the needs of a specific API.
**Snug** aims only to provide a versatile base,
so you can focus on what makes your API unique.


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

1. *Flexibility*. Since queries are just generators,
   customizing them requires no special glue-code.
   For example: add validation logic, or use any serialization method:

   .. code-block:: python

     from my_types import User, UserSchema

     def user(name: str) -> snug.Query[User]:
         """lookup a user by their username"""
         if len(name) == 0:
             raise ValueError('username must have >0 characters')
         request = snug.GET(f'https://api.github.com/users/{name}')
         response = yield request
         return UserSchema().load(json.loads(response.content))

2. *Effortlessly async*. The same query can also be executed asynchronously:

   .. code-block:: python

      query = repo('Hello-World', owner='octocat')
      repo = await snug.execute_async(query)

3. *Pluggable clients*. Queries are fully agnostic of the HTTP client.
   For example, to use `requests <http://docs.python-requests.org/>`_
   instead of the standard library:

   .. code-block:: python

      import requests
      execute = snug.executor(client=requests.Session())
      execute(repo('Hello-World', owner='octocat'))
      # {"description": "My first repository on Github!", ...}

4. *Testable*. Since queries are just generators, we can run them
   just fine without touching the network.
   No need for complex mocks or monkeypatching.

   .. code-block:: python

      >>> query = iter(repo('Hello-World', owner='octocat'))
      >>> next(query).url.endswith('/repos/octocat/Hello-World')
      True
      >>> query.send(snug.Response(200, b'...'))
      StopIteration({"description": "My first repository on Github!", ...})

5. *Swappable authentication*. Different credentials can be used to execute
   the same query:

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
          def __init__(self, name, owner): ...

          def __iter__(self): ...  # query of the repo itself

          def issue(self, num: int) -> snug.Query[dict]:
              """retrieve an issue in this repository by its number"""
              r = snug.GET(f'/repos/{self.owner}/{self.name}/issues/{num}')
              return json.loads((yield r).content)

      hello_world_repo = repo('Hello-World', owner='octocat')
      issue_348 = hello_world_repo.issue(348)
      snug.execute(issue_348)
      # {"title": "Testing comments", ...}

      # we could take this as far as we like, eventually:
      new_comments = (repo('Hello-World', owner='octocat')
                      .issue(348)
                      .comments(since=datetime(2018, 1, 1)))


7. *Function- or class-based? You decide*.
   Use class-based queries and inheritance to keep everything DRY:

   .. code-block:: python

      class BaseQuery(snug.Query):
          """base github query"""

          def prepare(self, request): ...  # add url prefix, headers, etc.

          def __iter__(self):
              request = self.prepare(self.request)
              return self.load(self.check_response((yield request)))

          def check_response(self, result): ...

      class repo(BaseQuery):
          """get a repo by owner and name"""
          def __init__(self, name, owner):
              self.request = snug.GET(f'/repos/{owner}/{name}')

          def load(self, response):
              return my_repo_loader(response.content)

      class follow(BaseQuery):
          """follow another user"""
          def __init__(self, name):
              self.request = snug.PUT(f'/user/following/{name}')

          def load(self, response):
              return response.status_code == 204

   Or, if you're comfortable with high-order functions and decorators,
   make use of `gentools <http://gentools.readthedocs.io/>`_
   to modify query ``yield``, ``send``, and ``return`` values:

   .. code-block:: python

      from gentools import (map_return, map_yield, map_send,
                            compose, oneyield)

      class Repository: ...

      def my_repo_loader(...): ...

      def my_error_checker(...): ...

      def my_request_preparer(...): ...  # add url prefix, headers, etc.

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


For more info, check out the `tutorial <http://snug.readthedocs.io/en/latest/tutorial.html>`_,
`recipes <http://snug.readthedocs.io/en/latest/recipes.html>`_,
or the examples (in the ``examples/`` directory)
