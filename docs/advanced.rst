.. _advanced:

Advanced topics
===============

This sections continues where the :ref:`tutorial <tutorial>` left off,
describing more advanced functionality.

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

We can use a function-based approach with
`gentools <http://gentools.readthedocs.io/>`_,
or a class-based approach by subclassing :class:`~snug.core.Query`.
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

The github API is full of related queries.
For example: creating a new issue related to a repository,
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


Authentication methods
----------------------

The default authentication method is HTTP Basic authentication.
To use another type of authentication,
use the ``auth_method`` argument
of :func:`~snug.core.executor`/:func:`~snug.core.async_executor`.

``auth_method`` will be called with credentials (the ``auth`` parameter),
and its result will be called with a :class:`~snug.core.Request` to authenticate.

To illutrate, here is a simple example for token-based authentication:

.. code-block:: python3

   class TokenAuth:
       def __init__(self, token):
           self.token = token

       def __call__(self, request):
           return request.with_headers({
               'Authorization': f'token {self.token}'
           })

   exec = snug.executor(auth='my token', auth_method=TokenAuth)

See the slack API example for a real-world use-case.
