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

Django-like querysets
---------------------

Class-based queries can be used to create a queryset-like API.
We can use github's issues endpoint to illustrate:

.. code-block:: python3

   import snug

   class issues(snug.Query):
       """select assigned issues within an organization"""

       def __init__(self, org, state='open', labels='', sort='created',
                    direction='desc', since=None):
           self.org = org
           self.params = {
               'state': state,
               'labels': labels,
               'sort': sort,
               'direction': direction,
           }
           if since:
               self.params['since'] = since

       def filter(self, state=None, labels=None):
           updated = self.params.copy()
           if state is not None: updated['state'] = state
           if labels is not None: updated['labels'] = labels
           return issues(self.org, **updated)

       def ascending(self):
           return issues(self.org, **{**self.params, 'direction': 'asc'})

       def sort_by(self, sort):
           return issues(self.org, **{**self.params, 'sort': sort})

       def __iter__(self):
           req = snug.GET(f'https://api.github.com/orgs/{self.org}/issues',
                          params=self.params)
           resp = yield req
           return json.loads(resp.content)


The resulting query class can be used as follows:

   >>> my_query = (issues(org='github')
   ...            .filter(state='all')
   ...            .filter(labels='bug,ui')
   ...            .sort_by('updated')
   ...            .ascending())
   ...
   >>> snug.execute(my_query, auth=('me', 'password'))
   [{"number": ..., ...}, ...]


Method chaining
---------------

With the following helper class, it is possible to
access all query functionality by method chaining:

.. code-block:: python3

   import snug

   class Explorer:

       def __init__(self, obj, *, executor=snug.execute):
           self.__wrapped__ = obj
           self._executor = executor

       def execute(self, **kwargs):
           """execute the wrapped object as a query

           Parameters
           ----------
           **kwargs
               arguments passed to the executor
           """
           return self._executor(self.__wrapped__, **kwargs)

       def __getattr__(self, name):
           """return an attribute of the underlying object, wrapped"""
           return Explorer(getattr(self.__wrapped__, name),
                           executor=self._executor)

       def __repr__(self):
           return f'Explorer({self.__wrapped__!r})'

       def __call__(self, *args, **kwargs):
           """call the underlying object, wrapping the result"""
           return Explorer(self.__wrapped__(*args, **kwargs),
                           executor=self._executor)

       def paginated(self):
           """make the wrapped query paginated"""
           return Explorer(snug.paginated(self.__wrapped__))


This allows us to write expressions like this:

.. code-block:: python3

   import github

   bound_ghub = Explorer(github, executor=...)
   issues = (bound_ghub.repo('Hello-World', owner='octocat')
             .issues(state='closed')
             .paginated()
             .execute())

   # instead of:
   issues = snug.execute(snug.paginated(
       my_github.repo('Hello-World', owner='octocat')
       .issues(state='closed')))
