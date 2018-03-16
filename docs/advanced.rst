.. _advanced_topics:

Advanced topics
===============

This sections continues where the :ref:`tutorial <tutorial>` left off,
describing more advanced functionality.

Executors
---------

To make it easier to call :func:`~snug.query.execute`/:func:`~snug.query.execute_async`
repeatedly with specific arguments,
the :func:`~snug.query.executor`/:func:`~snug.query.async_executor`
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
or a class-based approach by subclassing :class:`~snug.query.Query`.
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
The github API, for example is full of related queries:
creating a new issue related to a repository,
or retrieving gists for a user.

Below is an example of the ``repo`` query extended with related queries.
It demonstrates two ways of declaring related queries:

* as a method
* as a nested class with the :func:`~snug.query.related` decorator.

.. literalinclude:: ../tutorial/relations.py
   :emphasize-lines: 15,20,33

The ``repo`` query behaves the same as in the previous examples,
only it now has two related queries: ``star`` and ``issue``,
which has a related query of its own (``comments``).

The related queries allow us to write:

.. code-block:: python3

   >>> import tutorial.relations as ghub
   >>> exec = snug.executor(auth=('me', 'password'))
   >>>
   >>> hello_repo = ghub.repo('Hello-World', owner='octocat')
   >>> exec(hello_repo)
   {"description": "My first repository on Github!", ...}
   >>> exec(hello_repo.star())
   True
   >>> comments = hello_repo.issue(348).comments(since=datetime(2018, 1, 1))
   >>> exec(comments)
   [{"body": ...}, ...]


Authentication methods
----------------------

The default authentication method is HTTP Basic authentication.
To use another type of authentication,
pass a callable as the ``auth`` parameter
of :func:`~snug.query.executor`/:func:`~snug.query.async_executor`.

This callable takes a :class:`~snug.http.Request`,
and should return an authenticated copy.

To illutrate, here is a simple example for token-based authentication:

.. code-block:: python3

   class Token:
       def __init__(self, token):
           self._headers = {'Authorization': f'token {token}'}

       def __call__(self, request):
           return request.with_headers(self._headers)

   exec = snug.executor(auth=Token('my token'))

See the slack API example for a real-world use-case.

Full customization
------------------

One of the main advantages of queries is that they can be executed
with any HTTP client.
However, it may occur that advanced, client-specific features are needed.
For example, streaming data or multipart requests/responses.

For this purpose, you can use the
:meth:`~snug.query.Query.__execute__`\/:meth:`~snug.query.Query.__execute_async__` hook.
Implementing this method allows full customization of a query's execution.
The downside is that the query will become dependent
on the client, which limits its reusability.

The :meth:`~snug.query.Query.__execute__`\/:meth:`~snug.query.Query.__execute_async__`
methods take two (positional) arguments:

* ``client`` -- the client which was passed to :func:`~snug.query.execute`.
* ``auth`` -- a callable which takes a :class:`~snug.http.Request`,
  and returns an authenticated :class:`~snug.http.Request`.

The following example shows how this can be used to implement streaming responses
to download github repository `assets <https://developer.github.com/v3/repos/releases/#get-a-single-release-asset>`_.

.. code-block:: python3

   class asset_download(snug.Query):
       """streaming download of a repository asset.
       Can only be executed with the `requests` or `aiohttp` client"""

       def __init__(self, repo_name, repo_owner, id):
           self.request = snug.GET(
               f'https://api.github.com/repos/{repo_owner}'
               f'/{repo_name}/releases/assets/{id}',
               headers={'Accept': 'application/octet-stream'})

       def __execute__(self, client, auth):
           """executes the query, returning a streaming requests response"""
           assert isinstance(client, requests.Session)
           req = auth(self.request)
           return client.request(req.method, req.url,
                                 data=req.content,
                                 params=req.params,
                                 headers=req.headers,
                                 stream=True)

       async def __execute_async__(self, client, auth):
           """executes the query, returning an aiohttp response"""
           assert isinstance(client, aiohttp.Session)
           req = auth(self.request)
           return client.request(req.method, req.url,
                                 data=req.content,
                                 params=req.params,
                                 headers=req.headers)


We can then write:

.. code-block:: python3

   download = asset_download('hub', repo_owner='github', id=4187895)

   # with requests:
   response = snug.execute(download, client=requests.Session())
   for chunk in response.iter_content():
       ...

   # with aiohttp (inside a coroutine)
   async with aiohttp.Session() as s:
       response = snug.execute_async(download, client=s)

       while True:
           chunk = await resp.content.read(chunk_size)
           ...

.. note::

   You shouldn't have to use this feature very often.
   Its purpose is to provide an "escape hatch" to circumvent
   the usual query execution logic.
   If you find yourself using it often,
   consider posting a `feature request <https://github.com/ariebovenberg/snug/issues>`_
   for your use-case.

Registering HTTP clients
------------------------

By default, clients for `requests <http://docs.python-requests.org/>`_
and `aiohttp <http://aiohttp.readthedocs.io/>`_ are registered.
Register new clients with :func:`~snug.clients.send` or :func:`~snug.clients.send_async`.

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

Python 2 support
----------------

Writing python2-compatible queries is supported, with two important caveats:

1. Returning values from generators is not natively supported in python2.
   Use the :func:`~gentools.core.py2_compatible` decorator
   from `gentools <http://gentools.readthedocs.io/>`_ to do this.
   The resulting query can be run on python 2 and 3.

.. code-block:: python

    from gentools import py2_compatible, return_

    @py2_compatible
    def repo(name, owner):
        """get a github repo by owner and name"""
        request = snug.GET(f'https://api.github.com/repos/{owner}/{name}')
        response = yield request
        return_(json.loads(response.content))

2. Async functionality is not available on python2. Nonetheless,
   Python2-compatible queries can be run asychronously on python3.
