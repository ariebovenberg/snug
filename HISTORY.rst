Release history
---------------

development
+++++++++++

2.2.0 (2021-05-14)
++++++++++++++++++

- Update build with poetry, github actions

2.1.0 (2020-12-04)
++++++++++++++++++

- Add Python 3.9 support, drop 3.5.

2.0.0 (2019-10-27)
++++++++++++++++++

- Add Python 3.8 support
- Drop Python 2 support
- Adopt ``black`` autoformatter
- Fix error on import when no event loop is available

1.4.1 (2019-03-30)
++++++++++++++++++

- Small fix in pypi package metadata

1.4.0 (2019-03-30)
++++++++++++++++++

- Drop python 3.4 support (#83)

1.3.4 (2018-10-27)
++++++++++++++++++

- Fix deprecation warning on python 3.7 (#35)

1.3.3 (2018-10-25)
++++++++++++++++++

- Fix issue where ``urllib`` client would 
  raise ``HTTPError`` on HTTP error status codes (#33).

1.3.2 (2018-08-27)
++++++++++++++++++

- improvements to documentation

1.3.1 (2018-08-25)
++++++++++++++++++

- official python 3.7 support
- small fixes to documentation

1.3.0 (2018-05-13)
++++++++++++++++++

- remove deprecated ``auth_method`` parameter in ``execute()``

1.2.1 (2018-03-26)
++++++++++++++++++

- fix in README

1.2.0 (2018-03-21)
++++++++++++++++++

- ``auth`` parameter accepts callables
- deprecate ``auth_method`` parameter (to remove in version 1.3)
- paginated queries
- make ``asyncio`` client more robust
- added two new recipes

1.1.3 (2018-03-07)
++++++++++++++++++

- remove ``tutorial`` directory from build

1.1.2 (2018-03-07)
++++++++++++++++++

- fixes to docs

1.1.1 (2018-03-04)
++++++++++++++++++

- fixes to docs

1.1.0 (2018-03-04)
++++++++++++++++++

- python 2 compatibility
- implement overridable ``__execute__``, ``__execute_async__``
- improvements to ``aiohttp``, ``urllib`` clients

1.0.2 (2018-02-18)
++++++++++++++++++

- fixes for sending requests with default clients
- improvements to docs

1.0.1 (2018-02-12)
++++++++++++++++++

- improvements to docs
- fix for ``send_async``

1.0.0 (2018-02-09)
++++++++++++++++++

- improvements to docs
- added slack API example
- ``related`` decorator replaces ``Relation`` query class
- bugfixes

0.5.0 (2018-01-30)
++++++++++++++++++

- improvements to docs
- rename Request/Response data->content
- ``Relation`` query class

0.4.0 (2018-01-24)
++++++++++++++++++

- removed generator utils and serialization logic (now seperate libraries)
- improvements to docs

0.3.0 (2018-01-14)
++++++++++++++++++

- generator-based queries

0.1.2
+++++

- fixes to documentation

0.1.1
+++++

- improvements to versioning info

0.1.0
+++++

- implement basic resource and simple example
