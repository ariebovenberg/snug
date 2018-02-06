Recipes
=======

This page features some interesting recipes for common use-cases.


GraphQL
-------

A rudimentary example using the Github GraphQL API v4,
similar to the ``repo`` query in the tutorial:

.. code-block:: python

  from gentools import relay

  @relay
  def graphql(request: str):
      """decorator for GraphQL requests"""
      response = yield snug.POST('https://api.gitub.com/graphql',
                                 content=json.dumps({'query': request}))
      return json.loads(response.content)['data']


  @graphql
  def repo(name, owner, *, fields=('id', )):
      """lookup a repo by owner and name, returning only certain fields"""
      response = yield f'''
        query {
          repository(owner: "{owner}", name: "{name}") {
             {"\n".join(fields)}
          }
        }
      '''
      return response['repository']

Conditional requests
--------------------

Many APIs support conditional requests with ``If-None-Match``
or ``If-Modified-Since`` headers.
The example below shows a reusable implementation using
:class:`~gentools.core.relay`:

.. code-block:: python

  from gentools import relay

  class NotModified(Exception):
      pass

  @relay
  def if_modified_since(req):
      """decorator for queries supporting 'If-Modified-Since' headers"""
      resp = yield req
      if 'If-Modified-Since' in req.headers and resp.status_code == 304:
          raise NotModified
      return resp

  @if_modified_since
  def repo(name, owner, modified_since=None):
      """lookup a repo, or raise NotModified"""
      response = yield snug.GET(
          f'https://api.github.com/repos/{owner}/{name}',
          headers=({'If-Modified-Since': modified_since}
                   if modified_since else {}))
      return json.loads(response.content)

Pagination
----------

Pagination is one of the things that each API seems to do differently.
One way of implementing pagination is to return some sort
of ``Page`` object containing the current list of objects,
together with queries referencing the next pages.
This way, paginating through results becomes explicit.

Below is an example of the slack web API,
which uses cursor-based pagination.

.. code-block:: python3

   class Page:
       def __init__(self, objects, next_cursor):
           self.objects, self.next_cursor = objects, next_cursor

   def list_channels(cursor=None) -> snug.Query[Page]:
       """list slack channels"""
       request = snug.GET(f'https://slack.com/api/channels.list',
                          params={'cursor': cursor} if cursor else {})
       response = yield request
       raw_obj = json.loads(response.content)
       next_cursor = raw_obj['response_metadata']['next_cursor']
       return Page(raw_obj['channels'],
                   # next_cursor may be None
                   next=next_cursor and list_channels(cursor=next_cursor))

The query is then usable as:

.. code-block:: python3

   >>> exec = snug.executor(auth=...)
   >>> page1 = exec(list_channels())
   >>> list(page1)
   [{"name": ...}, ...]
   >>> page2 = exec(page1.next)
   >>> list(page2)
   [{"name": ...}, ...]
   >>> exec(page2.next)
   [{"name": ...}, ...]
