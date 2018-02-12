.. _advanced_topics:

Advanced topics
===============

This sections continues where the :ref:`tutorial <tutorial>` left off,
describing more advanced functionality.

Executors
---------

To make it easier to call :func:`~snug.execute`/:func:`~snug.execute_async`
repeatedly with specific arguments,
the :func:`~snug.executor`/:func:`~snug.async_executor`
shortcut can be used.

.. code-block:: python3

   import requests
   exec = snug.executor(auth=('me', 'password'),
                        client=requests.Session())
   exec(some_query)
   exec(other_query)

   # we can still override arguments
   exec(another_query, auth=('bob', 'hunter2'))

.. _composing:

Composing queries
-----------------

To keep everything nice and modular, queries may be composed and extended.
In the github API example, we may wish to define common logic for:

* prefixing urls with ``https://api.github.com``
* setting the required headers
* parsing responses to JSON
* deserializing JSON into objects
* raising descriptive exceptions from responses
* following redirects

We can use a function-based approach with
`gentools <http://gentools.readthedocs.io/>`_,
or a class-based approach by subclassing :class:`~snug.Query`.
We'll explore the functional style first.

Function-based approach
~~~~~~~~~~~~~~~~~~~~~~~

Preparing requests
^^^^^^^^^^^^^^^^^^

Outgoing requests of a query can be modified with
the :class:`~gentools.core.map_yield` decorator.

.. literalinclude:: ../tutorial/composed0.py
   :lines: 3-21
   :emphasize-lines: 10,16

Parsing responses
^^^^^^^^^^^^^^^^^

Responses being sent to a query can be modified with
the :class:`~gentools.core.map_send` decorator.

.. literalinclude:: ../tutorial/composed2.py
   :lines: 3-4,11-36
   :emphasize-lines: 17,24

Relaying queries
^^^^^^^^^^^^^^^^

For advanced cases, each requests/response interaction of a query
can be relayed through another generator.
This can be done with the :class:`~gentools.core.relay` decorator.
This can be useful if response handling is dependent on the request,
or more complex control flow.
The following example shows how this can be used to implement redirects.

.. literalinclude:: ../tutorial/composed3.py
   :lines: 3-4,24-36
   :emphasize-lines: 10

See the :ref:`recipes <recipes>` for more examples.


Loading return values
^^^^^^^^^^^^^^^^^^^^^

To modify the return value of a generator,
use the :class:`~gentools.core.map_return` decorator.

.. literalinclude:: ../tutorial/composed4.py
   :lines: 3-5,12-13,33-43
   :emphasize-lines: 11

Object-oriented approach
~~~~~~~~~~~~~~~~~~~~~~~~

Below is a roughly equivalent, object-oriented approach:

.. literalinclude:: ../tutorial/composed_oop.py

.. _nested:

Related queries
---------------

With class-based queries, it is possible to create an
expressive, chained API. 

For example, the github API is full of related queries:
creating a new issue related to a repository,
or retrieving gists for a user.

Below is an example of the ``repo`` query extended with related queries

.. literalinclude:: ../tutorial/relations.py
   :lines: 12-15,35-67

The ``repo`` query behaves the same as in the previous examples,
only it now has two related queries ``new_issue`` and ``star``.
The related queries allow us to write:

.. code-block:: python3

   >>> import tutorial.relations as ghub
   >>> exec = snug.executor(auth=('me', 'password'))
   >>>
   >>> hello_repo = ghub.repo('Hello-World', owner='octocat')
   >>> new_issue = hello_repo.new_issue('found a bug')
   >>> star_repo = hello_repo.star()
   >>> exec(new_issue)
   Issue(...)
   >>> exec(star_repo)
   True


Authentication methods
----------------------

The default authentication method is HTTP Basic authentication.
To use another type of authentication,
use the ``auth_method`` argument
of :func:`~snug.executor`/:func:`~snug.async_executor`.

``auth_method`` will be called with credentials (the ``auth`` parameter),
and a :class:`~snug.Request` instance.
It should return an authenticated request.

To illutrate, here is a simple example for token-based authentication:

.. code-block:: python3

   def token_auth(token, request)
       return request.with_headers({'Authorization': f'token {token}'})

   exec = snug.executor(auth='my token', auth_method=token_auth)

See the slack API example for a real-world use-case.

Registering HTTP clients
------------------------

By default, clients for `requests <http://docs.python-requests.org/>`_
and `aiohttp <http://aiohttp.readthedocs.io/>`_ are registered.
Register new clients with :func:`~snug.send` or :func:`~snug.send_async`.

These functions are :func:`~functools.singledispatch` functions.
A new client type can be registered as follows:

.. code-block:: python3

   @snug.send.register(MyClientType)
   def _send(client: MyClientType, req: snug.Request) -> snug.Response:
       # unpack the snug.Request into a client call
       raw_response = client.send_request(
           url=req.url,
           data=req.content,
           ...)

       # be sure to wrap the response in a snug.Response before returning
       return snug.Response(
           status_code=raw_response.status_code,
           ...)
