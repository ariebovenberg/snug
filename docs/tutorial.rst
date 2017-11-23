Tutorial
========

.. currentmodule:: snug

This guide explains how to use the building-blocks that ``snug`` provides.
In this example, we will be wrapping the github v3 REST API.

.. warning::

   this tutorial is not yet finished

Hello query
-----------

The main building block we'll be working with is :class:`~snug.query.Query`.
Queries represent requests to the API, which may be resolved to python objects.

Let's start by creating a simple query for repo's.

.. literalinclude:: ../tutorial/hello_query.py
   :linenos:


Our module is now usable as follows:

.. code-block:: python

   >>> import tutorial.hello_query as ghub
   >>> repo_lookup = ghub.repo('Hello-World', owner='octocat')
   >>> repo = ghub.resolve(repo_lookup)
   >>> repo['description']
   'My first repository on GitHub!'
   >>> repo['created_at']
   '2011-01-26T19:01:12Z'

.. note::

   ``simple_resolve`` has defaults set up for JSON-based APIs.
   See :ref:`non-json-data` for working with non-JSON data (e.g. XML).


Loading objects
---------------

Returning a ``dict`` for our repo is not very nice though.
In order to convert to neat python objects, we can specify the result-type
of our query:

.. literalinclude:: ../tutorial/loading_objects.py
   :linenos:
   :emphasize-lines: 1,2,5-9,11


Resolving our query now returns the given type:

.. code-block:: python

   >>> import tutorial.loading_objects as ghub
   >>> repo_lookup = ghub.repo('Hello-World', owner='octocat')
   >>> repo = ghub.resolve(repo_lookup)
   >>> repo.description
   'My first repository on GitHub!'
   >>> repo.created_at
   datetime.datetime(2011, 1, 26, 19, 1, 12)


.. note::

   ``simple_resolve`` does a best guess on how to load the given
   datatype. For more control over this behavior, see :ref:`customizing-loaders`.


Nested queries
--------------

Let's exapand our wrapper with issues. We could create a new query,
alongside ``repo``, but since issues are linked to a single repo
it makes sence to nest them. We can do this by using :class:`~snug.query.Query` subclassing.

.. literalinclude:: ../tutorial/nested_queries.py
   :linenos:
   :emphasize-lines: 5-9,17-30

The ``repo`` query behaves the same as in the previous examples,
only it now has a nested query ``issue``.
The nested query allows us to write:

.. code-block:: python

   >>> import tutorial.nested_queries as ghub
   >>> issue_lookup = ghub.repo('Hello-World', owner='octocat').issue(349)
   >>> issue = ghub.resolve(issue_lookup)
   >>> issue.number
   349
   >>> issue.title
   'Testing reactions'


Api configuration
-----------------

Authentication
--------------

TODO

HTTP clients
------------

.. todo::
   expand this section

The default HTTP client is a ``requests.Session``.
The HTTP client is set by the ``client`` argument of ``resolve``.
To register a new HTTP client type,
register it with the ``singledispatch`` function ``snug.http.send``

.. _customizing-loaders:

Customizing loaders
-------------------

.. todo::
   write this section


Pagination
----------

.. todo::
   implement this feature

.. _non-json-data:

Non-JSON data
-------------

.. todo::
   write this section
