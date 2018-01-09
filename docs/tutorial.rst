Tutorial
========

.. currentmodule:: snug

This guide explains how to use the building-blocks that ``snug`` provides.
In this example, we will be wrapping the github v3 REST API.

.. warning::

   this tutorial is not yet finished

Hello query
-----------

The basic building block we'll be working with is the *query*,
A query represents an interaction with the API which may be executed.
A simple way to define a query
is by a :term:`generator function <generator>`.

Let's start by creating a lookup query for repositories.

.. literalinclude:: ../tutorial/hello_query.py
   :linenos:

We can see from the example that a query:

* yields requests
* recieves responses
* returns an outcome

Our module is now usable as follows:

.. code-block:: python

   >>> import tutorial.hello_query as ghub
   >>> query = ghub.repo('Hello-World', owner='octocat')
   >>> repo = ghub.exec(query)
   >>> repo['description']
   'My first repository on GitHub!'

.. admonition:: Why generators?

   Expressing queries as generators has two main advantages:

   1. as built-in concepts of the language, generators can be easily
      :ref:`composed and extended<composing>`.
   2. decoupling of networking logic allows
      the :ref:`use different HTTP (asynchronous) clients<executors>`.


.. admonition:: What's in a query?

   Any object whose :meth:`~collections.abc.Iterable.__iter__` returns a generator
   may be considered a :class:`~snug.core.Query`.
   (This includes any :term:`generator iterator` created by
   a :term:`generator function <generator>`.)
   The example below shows a query class roughly equivalent
   to our previously defined ``repo``.
   
   .. literalinclude:: ../tutorial/query_api.py
     :pyobject: repo
     :linenos:


.. _executors:

Executors
---------

Queries can be executed by different executors.
Lets add another query, and see the different ways it may be executed.

.. literalinclude:: ../tutorial/executors.py
   :lines: 11-23
   :linenos:
   :emphasize-lines: 10,12

We can make use of the module as follows:

.. code-block:: python

   >>> import snug
   >>> import tutorial.executors as ghub
   >>> # an example query
   >>> follow_the_octocat = ghub.follow('octocat')

   >>> # using different credentials
   >>> exec_as_me = ghub.authed_exec(('me', 'password'))
   >>> exec_as_other = ghub.authed_exec(('other', 'hunter2'))
   >>> exec_as_me(follow_the_octocat)
   True
   >>> exec_as_other(follow_the_octocat)
   True

   >>> # using another HTTP client, for example `requests`
   >>> import requests
   >>> exec = ghub.authed_exec(
   ...     ('me', 'password'),
   ...     sender=snug.http.requests_sender(requests.Session()))
   >>> exec(follow_the_octocat)
   True

   >>> # the same query may also be executed asynchronously with `aiohttp`
   >>> import asyncio
   >>> import aiohttp
   >>> async def main():
   ...     async with aiohttp.ClientSession() as session:
   ...         aexec = ghub.authed_aexec(
   ...             ('me', 'password'),
   ...             sender=snug.http.aiohttp_sender(session)
   ...         return await aexec(follow_the_octocat)
   >>> loop = asyncio.get_event_loop()
   >>> loop.run_until_complete(main())
   True

.. _composing:

Composing queries
-----------------

To keep everything DRY, queries may be composed and extended.
In our github API example, we may wish to define common logic for:

* prefixing urls with ``https://api.github.com``
* setting the required headers
* parsing responses to JSON
* deserializing JSON into objects
* raising descriptive exceptions from responses
* follows redirects

Preparing requests
^^^^^^^^^^^^^^^^^^

Outgoing requests of a query can be modified with
the :class:`~snug.core.yieldmapped` decorator.

.. literalinclude:: ../tutorial/composing_queries.py
   :linenos:
   :lines: 7-23
   :emphasize-lines: 8,14

:class:`~snug.core.yieldmapped` may take several callables,
which are then applied right-to-left to everything the generator yields.


Parsing responses
^^^^^^^^^^^^^^^^^

Responses being sent to a query can be modified with
the :class:`~snug.core.sendmapped` decorator.

.. literalinclude:: ../tutorial/composing_queries2.py
   :lines: 13-38
   :linenos:
   :emphasize-lines: 15,22

Nesting queries
^^^^^^^^^^^^^^^

For advanced cases, queries may also be nested.
The following example shows how this can be used to implement redirects.

.. literalinclude:: ../tutorial/composing_queries3.py
   :lines: 26-38
   :linenos:
   :emphasize-lines: 8


Related queries
---------------

The github API is full of related queries:
for example, creating a new issue related to a repository,
or retrieving gists for a user.

We can make use of query classes:


.. literalinclude:: ../tutorial/relations.py
   :lines: 12-13,33-60
   :linenos:
   :emphasize-lines: 14,24

The ``repo`` query behaves the same as in the previous examples,
only it now has two related queries ``new_issue`` and ``star``.
The related queries allow us to write:

.. code-block:: python

   >>> import tutorial.relations as ghub
   >>> hello_repo = ghub.repo('Hello-World', owner='octocat')
   >>> new_issue = hello_repo.new_issue('found a bug')
   >>> star_repo = hello_repo.star()
   >>> ghub.exec(new_issue)
   Issue(...)
   >>> ghub.exec(star_repo)
   True

.. _customizing-loaders:

Deserialization tools
---------------------

.. todo::
   write this section
