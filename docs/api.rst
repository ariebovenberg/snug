API reference
=============

.. automodule:: snug

Query
-----

.. automodule:: snug.query
   :members:
   :special-members:
   :exclude-members: __next_in_mro__,__weakref__,__mro__,__init__,__repr__,\
      ,__eq__,__ne__,__hash__,__len__

HTTP
----

.. automodule:: snug.http
   :members:
   :special-members:
   :exclude-members: __next_in_mro__,__weakref__,__mro__,__init__,__repr__,\
      ,__eq__,__ne__,__hash__,__len__


.. autofunction:: snug.http.GET
.. autofunction:: snug.http.POST
.. autofunction:: snug.http.PUT
.. autofunction:: snug.http.PATCH
.. autofunction:: snug.http.DELETE
.. autofunction:: snug.http.HEAD
.. autofunction:: snug.http.OPTIONS
.. autodata:: snug.http.header_adder
.. autodata:: snug.http.prefix_adder


Pagination
----------

.. automodule:: snug.pagination

.. autoclass:: snug.pagination.paginated
   :members: __execute__, __execute_async__

.. autoclass:: snug.pagination.Page

.. autoclass:: snug.pagination.Pagelike
   :members:


Clients
-------

.. automodule:: snug.clients
   :members:
   :special-members:
   :exclude-members: __next_in_mro__,__weakref__,__mro__,__init__,__repr__,\
      ,__eq__,__ne__,__hash__,__len__
