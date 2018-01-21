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


A microframework for HTTP clients.

Quickstart
----------

1. API interactions ("queries") are request/response generators:

  .. code-block:: python

    import json
    import snug

    def repo(name: str, owner: str):
        """a repo lookup by owner and name"""
        request = snug.GET(
            f'https://api.github.com/repos/{owner}/{name}')
        response = yield request
        return json.loads(response.data)

2. Queries can be executed

  .. code-block:: python

    >>> query = repo('Hello-World', owner='octocat')
    >>> snug.execute(query)
    {"description": "My first repository on Github!", ...}

3. That's it


Features
--------

1. *Simplicity*. If you understand generators, you understand queries.
   Customizing your query requires no special glue-code.
   For example: add your own validation logic,
   or use any serializer you like:

   .. code-block:: python

     from my_serializers import UserSchema

     def user(name: str):
         """lookup a user by their username"""
         if len(name) == 0:
             raise ValueError('username must have >0 characters')
         req = snug.GET(f'https://api.github.com/users/{name}')
         response = yield req
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

4. *Testable*. Since queries are just generators, we can run them
   just fine without touching the network.
   No need for complex mocks or monkeypatching.

   .. code-block:: python

      query = repo('Hello-World', owner='octocat')
      assert next(query).url.endswith('/repos/octocat/Hello-World')
      try:
          query.send(snug.Response(200, b'...'))
      except StopIteration as e:
          result = e.value
      assert result['name'] == 'Hello-World'

5. *Swappable authentication*. Different credentials can be used to execute
   the same query.

   .. code-block:: python

      def follow(name: str):
          """follow another user"""
          request = snug.PUT(
              'https://api.github.com/user/following/{name}')
          return (yield request).status_code == 204

      exec_as_me = snug.executor(auth=('me', 'password'))
      exec_as_bob = snug.executor(auth=('bob', 'password'))

      exec_as_me(follow('octocat'))
      exec_as_bob(follow('octocat'))

6. *Related queries*. Create a chained API for related objects:

   .. code-block:: python

      class repo(snug.Query):
          """a repo lookup by owner and name"""
          def __init__(self, name, owner):
              ...

          def __iter__(self):
              ...

          def issue(self, num):
              """an issue in this repository by its number"""
              url = f'/repos/{self.owner}/{self.name}/issues/{num}'
              return json.loads((yield snug.GET(url)).data)

      # the `repo` query works as before
      hello_world_repo = repo('Hello-World', owner='octocat')
      # ...but now we can make a related query
      issue_lookup = hello_world_repo.issue(348)
      snug.execute(issue_lookup)

7. *Composable*. If you're comfortable with high-order functions and decorators,
   make use of the ``gentools`` library to create generators
   and apply functions to a generator's
   ``yield``, ``send``, and ``return`` values.

   .. code-block:: python

      from gentools import (map_return, map_yield, map_send,
                            compose, oneyield)

      def my_repo_loader(...):
          ...  # e.g. create a nice Respository object

      def my_error_checker(...):
          ...  # e.g. raise descritive errors on HTTP 4xx responses

      def my_preparer(...):
          ...  # e.g. add headers, url prefix, etc

      basic_interaction = compose(map_send(my_error_checker),
                                  map_yield(my_preparer))

      @mapreturn(my_repo_loader)
      @basic_interaction
      @map_yield(snug.GET)
      @oneyield
      def repo(owner: str, name: str):
          """get a repo by owner and name"""
          return f'/repos/{owner}/{name}'

      @basic_interaction
      @map_yield(snug.PUT)
      def follow(username):
          """follow another user"""
          response = yield f'/user/following/{name}'
          return response.status_code == 204


Check the ``examples/`` directory for some samples.
