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

One way of implementing pagination is to return a ``Page`` object
with queries referencing the other pages:

.. code-block:: python

   from requests.utils import parse_header_links

   class StaticQuery(snug.Query):
       """a static GET query to an URL"""
       def __init__(self, url, loader):
           self.url, self.loader = url, loader

       def __iter__(self):
           return self.loader((yield snug.GET(self.url)))

   class Page:
       """a page of objects, with references to next pages"""
       def __init__(self, objects, next=None, last=None):
           self.objects, self.next, self.last = objects, next, last

       def __iter__(self):
           return iter(self.objects)

   def repo_issues(owner, name):
       """get a page of issues"""
       response = yield snug.GET(f'/repos/{owner}/{name}/issues')
       return _load_issue_page(response)

   def _load_issue_page(response):
       links = {
           link['rel']: link['url']
           for link in parse_header_links(response.headers['Link'])
       }
       nexturl = links.get('next')
       lasturl = links.get('last')
       return Page(
           objects=json.loads(response.content),
           next=nexturl and StaticQuery(nexturl, loader=_load_issue_page)
           last=lasturl and StaticQuery(lasturl, loader=_load_issue_page)
       )
