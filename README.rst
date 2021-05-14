Snug 🧣
=======

.. image:: https://img.shields.io/pypi/v/snug.svg
   :target: https://pypi.python.org/pypi/snug

.. image:: https://img.shields.io/pypi/l/snug.svg
   :target: https://pypi.python.org/pypi/snug

.. image:: https://img.shields.io/pypi/pyversions/snug.svg
   :target: https://pypi.python.org/pypi/snug

.. image:: https://github.com/ariebovenberg/snug/actions/workflows/tests.yml/badge.svg
   :target: https://github.com/ariebovenberg/snug

.. image:: https://img.shields.io/codecov/c/github/ariebovenberg/snug.svg
   :target: https://codecov.io/gh/ariebovenberg/snug

.. image:: https://img.shields.io/readthedocs/snug.svg
   :target: http://snug.readthedocs.io/

.. image:: https://img.shields.io/codeclimate/maintainability/ariebovenberg/snug.svg
   :target: https://codeclimate.com/github/ariebovenberg/snug/maintainability

.. image:: https://img.shields.io/badge/dependabot-enabled-brightgreen.svg?longCache=true&logo=dependabot
   :target: https://dependabot.com
   
.. image:: https://img.shields.io/badge/code%20style-black-000000.svg
   :target: https://github.com/psf/black


**Snug** is a tiny toolkit for writing reusable interactions with web APIs. Key features:

* Write once, run with different HTTP clients (sync *and* async)
* Fits any API architecture (e.g. REST, RPC, GraphQL)
* Simple, lightweight and versatile

Why?
----

Writing reusable web API interactions is difficult.
Consider a generic example:

.. code-block:: python

    import json

    def repo(name, owner):
        """get a github repo by owner and name"""
        request = Request(f'https://api.github.com/repos/{owner}/{name}')
        response = my_http_client.send(request)
        return json.loads(response.content)

Nice and simple. But...

* What about async? Do we write another function for that?
* How do we write clean unittests for this?
* What if we want to use another HTTP client or session?
* How do we use this with different credentials?

*Snug* allows you to write API interactions
independent of HTTP client, credentials, or whether they are run (a)synchronously.

In contrast to most API client toolkits,
snug makes minimal assumptions and design decisions for you.
Its simple, adaptable foundation ensures
you can focus on what makes your API unique.
Snug fits in nicely whether you're writing a full-featured API wrapper,
or just making a few API calls.

Quickstart
----------

1. API interactions ("queries") are request/response generators.

.. code-block:: python

  import snug

  def repo(name, owner):
      """get a github repo by owner and name"""
      request = snug.GET(f'https://api.github.com/repos/{owner}/{name}')
      response = yield request
      return json.loads(response.content)

2. Queries can be executed:

.. code-block:: python

  >>> query = repo('Hello-World', owner='octocat')
  >>> snug.execute(query)
  {"description": "My first repository on Github!", ...}

Features
--------

1. **Effortlessly async**. The same query can also be executed asynchronously:

   .. code-block:: python

      query = repo('Hello-World', owner='octocat')
      repo = await snug.execute_async(query)

2. **Flexibility**. Since queries are just generators,
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

3. **Pluggable clients**. Queries are fully agnostic of the HTTP client.
   For example, to use `requests <http://docs.python-requests.org/>`_
   instead of the standard library:

   .. code-block:: python

      import requests
      query = repo('Hello-World', owner='octocat')
      snug.execute(query, client=requests.Session())

4. **Testability**. Queries can easily be run without touching the network.
   No need for complex mocks or monkeypatching.

   .. code-block:: python

      >>> query = repo('Hello-World', owner='octocat')
      >>> next(query).url.endswith('/repos/octocat/Hello-World')
      True
      >>> query.send(snug.Response(200, b'...'))
      StopIteration({"description": "My first repository on Github!", ...})

5. **Swappable authentication**. Queries aren't tied to a session or credentials.
   Use different credentials to execute the same query:

   .. code-block:: python

      def follow(name: str) -> snug.Query[bool]:
          """follow another user"""
          req = snug.PUT('https://api.github.com/user/following/{name}')
          return (yield req).status_code == 204

      snug.execute(follow('octocat'), auth=('me', 'password'))
      snug.execute(follow('octocat'), auth=('bob', 'hunter2'))

6. **Related queries**. Use class-based queries to create an
   expressive, chained API for related objects:

   .. code-block:: python

      class repo(snug.Query[dict]):
          """a repo lookup by owner and name"""
          def __init__(self, name, owner): ...

          def __iter__(self): ...  # query for the repo itself

          def issue(self, num: int) -> snug.Query[dict]:
              """retrieve an issue in this repository by its number"""
              r = snug.GET(f'/repos/{self.owner}/{self.name}/issues/{num}')
              return json.loads((yield r).content)

      my_issue = repo('Hello-World', owner='octocat').issue(348)
      snug.execute(my_issue)

7. **Pagination**. Define paginated queries for (asynchronous) iteration.

   .. code-block:: python

      def organizations(since: int=None):
          """retrieve a page of organizations since a particular id"""
          resp = yield snug.GET('https://api.github.com/organizations',
                                params={'since': since} if since else {})
          orgs = json.loads(resp.content)
          next_query = organizations(since=orgs[-1]['id'])
          return snug.Page(orgs, next_query=next_query)

      my_query = snug.paginated(organizations())

      for orgs in snug.execute(my_query):
          ...

      # or, with async
      async for orgs in snug.execute_async(my_query):
          ...

8. **Function- or class-based? You decide**.
   One option to keep everything DRY is to use
   class-based queries and inheritance:

   .. code-block:: python

      class BaseQuery(snug.Query):
          """base github query"""

          def prepare(self, request): ...  # add url prefix, headers, etc.

          def __iter__(self):
              """the base query routine"""
              request = self.prepare(self.request)
              return self.load(self.check_response((yield request)))

          def check_response(self, result): ...  # raise nice errors

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

   Or, if you're comfortable with higher-order functions and decorators,
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
`advanced features <http://snug.readthedocs.io/en/latest/advanced.html>`_,
`recipes <http://snug.readthedocs.io/en/latest/recipes.html>`_,
or `examples <http://snug.readthedocs.io/en/latest/examples.html>`_.


Installation
------------

There are no required dependencies. Installation is easy as:

.. code-block:: bash

   pip install snug

Although snug includes basic sync and async HTTP clients,
you may wish to install `requests <http://docs.python-requests.org/>`_
and/or `aiohttp <http://aiohttp.readthedocs.io/>`_.

.. code-block:: bash

   pip install requests aiohttp


Alternatives
------------

If you're looking for a less minimalistic API client toolkit,
check out `uplink <http://uplink.readthedocs.io/>`_
or `tapioca <http://tapioca-wrapper.readthedocs.io/>`_.
