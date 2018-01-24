Tutorial
========

This guide explains how to use the building-blocks that ``snug`` provides.
In this example, we will be wrapping the github v3 REST API.

.. warning::

   this tutorial is still work-in-progress

Hello query
-----------

The basic building block we'll be working with is the *query*,
A query represents an interaction with the API which may be executed.
The simplest way to create a query is through a
:term:`generator function <generator>`.

Let's start by creating a lookup query for repositories.

.. literalinclude:: ../tutorial/hello_query.py

We can see from the example that a query:

* yields :class:`Requests<snug.core.Request>`
* recieves :class:`Responses<snug.core.Response>`
* returns an outcome

We can now import our module, and execture the query as follows:

.. code-block:: python3

   >>> import tutorial.hello_query as ghub
   >>> query = ghub.repo('Hello-World', owner='octocat')
   >>> repo = snug.execute(query)
   {"description": "My first repository on Github!", ...}

.. Note::

    Expressing queries as generators has two main advantages:

    1. as built-in concepts of the language, generators can be easily
       :ref:`composed and extended<composing>`.
    2. decoupling of networking logic allows
       the :ref:`use different and asynchronous HTTP clients<executors>`.

    We will explore these features in the following sections.

What's in a query?
------------------

Any object whose :meth:`~object.__iter__` returns a generator
may be considered a :class:`~snug.core.Query`.
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
          request = snug.GET(f'https://api.github.com/repos/{owner}/{name}')
          response = yield request
          return json.loads(response.data)

The main difference is that the class-based version is reusable:

>>> lookup = repo('Hello-World', owner='octocat')
>>> snug.execute(lookup)
>>> # not possible if `repo` was just a generator function
>>> snug.execute(lookup)

You can use :func:`~gentools.core.reusable`
(from the `gentools <https://github.com/ariebovenberg/gentools>`_ package)
to create reusable classes from generator functions automatically:

.. code-block:: python3

  from gentools import reusable

  @reusable
  def repo(...):
      ...

.. _executors:

Ways to execute your query
--------------------------

Queries can be executed by different executors.
Executors are callables which take a query
and return its outcome.
We've already seen a basic executor: :func:`~snug.core.execute`.
Lets add another query, and see the different ways it can be executed.

.. literalinclude:: ../tutorial/executors.py
   :lines: 2,4,12-

We can make use of the module as follows:

.. code-block:: python3

   >>> import snug
   >>> import tutorial.executors as ghub
   >>> # an example query
   >>> follow_the_octocat = ghub.follow('octocat')

   >>> # using different credentials
   >>> exec_as_me = snug.executor(auth=('me', 'password'))
   >>> exec_as_other = snug.executor(('other', 'hunter2'))
   >>> exec_as_me(follow_the_octocat)
   True
   >>> exec_as_other(follow_the_octocat)
   True

   >>> # using another HTTP client, for example `requests`
   >>> import requests
   >>> exec = snug.executor(('me', 'password'), client=requests.Session())
   >>> exec(follow_the_octocat)
   True

   >>> # the same query may also be executed asynchronously:
   >>> import asyncio
   >>> exec_async = ghub.async_executor(auth=('me', 'password'))
   >>> loop = asyncio.get_event_loop()
   >>> loop.run_until_complete(exec_async(follow_the_octocat))
   True

.. _composing:

Composing queries
-----------------

To keep everything nice and modular, queries may be composed and extended.
In our github API example, we may wish to define common logic for:

* prefixing urls with ``https://api.github.com``
* setting the required headers
* parsing responses to JSON
* deserializing JSON into objects
* raising descriptive exceptions from responses
* following redirects

We can use a functional approach with 
`gentools <https://github.com/ariebovenberg/gentools>`_,
or a more object-oriented approach by subclassing :class:`~snug.core.Query`.
We'll explore the functional style first.


Preparing requests
^^^^^^^^^^^^^^^^^^

Outgoing requests of a query can be modified with
the :class:`~gentools.core.map_yield` decorator.

.. literalinclude:: ../tutorial/composing_queries.py
   :lines: 3-4,11-21
   :emphasize-lines: 4,10

Parsing responses
^^^^^^^^^^^^^^^^^

Responses being sent to a query can be modified with
the :class:`~gentools.core.map_send` decorator.

.. literalinclude:: ../tutorial/composing_queries2.py
   :lines: 3-4,11-36
   :emphasize-lines: 17,24

Relaying queries
^^^^^^^^^^^^^^^^

For advanced cases, each requests/response interaction of a query
can be relayed through other generators.
This can be done with the :class:`~gentools.core.relay` decorator.
The following example shows how this can be used to implement redirects.

.. literalinclude:: ../tutorial/composing_queries3.py
   :lines: 3-4,24-36
   :emphasize-lines: 10


Loading return values
^^^^^^^^^^^^^^^^^^^^^

To modify the return value of a generator,
use the :class:`~gentools.core.map_return` decorator.

.. literalinclude:: ../tutorial/composing_queries4.py
   :lines: 3-5,12-13,33-43
   :emphasize-lines: 11


Related queries
---------------

The github API is full of related queries:
for example, creating a new issue related to a repository,
or retrieving gists for a user.

We can make use of query classes to express these relations.


.. literalinclude:: ../tutorial/relations.py
   :lines: 12-15,35-

The ``repo`` query behaves the same as in the previous examples,
only it now has two related queries ``new_issue`` and ``star``.
The related queries allow us to write:

.. code-block:: python3

   >>> import tutorial.relations as ghub
   >>> execute = snug.executor(auth=('me', 'password'))
   >>> hello_repo = ghub.repo('Hello-World', owner='octocat')
   >>> new_issue = hello_repo.new_issue('found a bug')
   >>> star_repo = hello_repo.star()
   >>> execute(new_issue)
   Issue(...)
   >>> execute(star_repo)
   True
