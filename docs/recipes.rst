.. _recipes:

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
  def repo(name, owner, *, fields=('id', )) -> snug.Query[dict]:
      """lookup a repo by owner and name, returning only certain fields"""
      response = yield f'''
        query {
          repository(owner: "{owner}", name: "{name}") {
             {"\n".join(fields)}
          }
        }
      '''
      return response['repository']

  q = repo('Hello-World', owner='octocat', fields=('description', 'id'))
  snug.execute(q)
  # {'description': ..., 'id': ...}

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

  q = repo('Hello-World', 'octocat', modified_since='2018-02-08T00:30:01Z')
  snug.execute(q)
  # NotModified()


Testing
-------

Because queries are generators, we can easily write unittests
that don't touch the network.

Here is an annotated example of testing the example gitub ``repo`` query:

.. code-block:: python3

   from gentools import sendreturn

   def test_repo():
       # iter() ensures this works for function- and class-based queries
       query = iter(repo('Hello-World', owner='octocat'))

       # check the request is OK
       request = next(query)
       assert request.url.endswith('repos/octocat/Hello-World')

       # construct our test response
       response = snug.Response(200, b'...<test response content>...')

       # getting the return value of a generator requires
       # catching StopIteration.
       # the following shortcut with `sendreturn` is equivalent to:
       #
       # try:
       #     query.send(response)
       # except StopIteration as e:
       #     result = e.value
       # else:
       #     raise RuntimeError('generator did not return')
       result = sendreturn(query, response)

       # check the result is OK
       assert result['description'] == 'My first repository on github!'

The slack and NS API tests show real-world cases for this.
