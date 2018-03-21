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


.. autodata:: snug.GET
.. autodata:: snug.POST
.. autodata:: snug.PUT
.. autodata:: snug.PATCH
.. autodata:: snug.DELETE
.. autodata:: snug.HEAD
.. autodata:: snug.OPTIONS


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
