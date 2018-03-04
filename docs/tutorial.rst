.. _tutorial:

Tutorial
========

This guide explains how to use the building-blocks that ``snug`` provides.
In this example, we will be wrapping the github v3 REST API.

Hello query
-----------

The basic building block we'll be working with is the *query*.
A query represents an interaction with the API which may be executed.
The simplest way to create a query is through a
:term:`generator function <generator>`.

Let's start by creating a lookup query for repositories.

.. literalinclude:: ../tutorial/hello_query.py

We can see from the example that a :class:`~snug.query.Query`:

* yields :class:`Requests<snug.http.Request>`
* recieves :class:`Responses<snug.http.Response>`
* returns an outcome (in this case, a :class:`dict`)

.. Note::

   You can ignore the type annotations if you like, they are not required.

We can now import our module, and execute the query as follows:

.. code-block:: python3

   >>> import tutorial.hello_query as ghub
   >>> query = ghub.repo('Hello-World', owner='octocat')
   >>> repo = snug.execute(query)
   {"description": "My first repository on Github!", ...}

Inside a coroutine, we can execute the same query asynchronously:

.. code-block:: python3

   query = ghub.repo('Hello-World', owner='octocat')
   repo = await snug.execute_async(query)

Expressing queries as generators has two main advantages:

1. as built-in concepts of the language, they can be easily
   :ref:`composed and extended<composing>`.
2. decoupling networking logic allows
   the :ref:`use different and async HTTP clients<executing_queries>`.

We will explore these features in the following sections.

Class-based queries
-------------------

Any object whose :meth:`~object.__iter__` returns a generator
may be considered a :class:`~snug.query.Query`.
(This includes :term:`generators <generator iterator>` themselves.)
The example below shows a query class equivalent
to our previously defined ``repo``.

.. code-block:: python3

  class repo(snug.Query[dict]):
      """a repository lookup by owner and name"""
      def __init__(self, name: str, owner: str):
          self.name, self.owner = name, owner

      def __iter__(self):
          owner, name = self.owner, self.name
          req = snug.GET(f'https://api.github.com/repos/{owner}/{name}')
          response = yield req
          return json.loads(response.content)

The main difference is that the class-based version is reusable:

>>> lookup = repo('Hello-World', owner='octocat')
>>> snug.execute(lookup)
>>> # not possible if `repo` was just a generator function
>>> snug.execute(lookup)

Additionally, class-based queries allow us
to define :ref:`nested queries<nested>`.

.. Note::

  You can use :func:`~gentools.core.reusable`
  (from the `gentools <http://gentools.readthedocs.io/>`_ package)
  to create reusable classes from generator functions automatically:

  .. code-block:: python3

    from gentools import reusable

    @reusable
    def repo(...):
        ...

.. _executing_queries:

Executing queries
-----------------

Queries can be executed in different ways.
We have already seen :func:`~snug.query.execute`
and :func:`~snug.query.execute_async`.
Both these functions take arguments which affect:

* which HTTP client is used
* which authentication credentials are used

To illustrate, let's add another query
and see the different ways it can be executed.

.. literalinclude:: ../tutorial/executing_queries.py
   :lines: 2,4,12-

We can make use of the module as follows:

.. code-block:: python3

   >>> import snug
   >>> import tutorial.executing_queries as ghub
   >>> # our example query
   >>> follow_the_octocat = ghub.follow('octocat')

   >>> # using different credentials
   >>> snug.execute(follow_the_octocat, auth=('me', 'password'))
   True
   >>> snug.execute(follow_the_octocat, auth=('bob', 'hunter2'))
   True

   >>> # using another HTTP client, for example `requests`
   >>> import requests
   >>> s = requests.Session()
   >>> snug.execute(follow_to_octocat, client=s, auth=('me', 'password'))
   True

   >>> # the same options are available for execute_async
   >>> import asyncio
   >>> future = snug.execute_async(follow_the_octocat,
   ...                             auth=('me', 'password'))
   >>> loop = asyncio.get_event_loop()
   >>> loop.run_until_complete(future)
   True

Read on about more advanced features :ref:`here <advanced_topics>`.
