Examples
========

The examples can be found in the ``/examples`` directory.
The exemples are not meant to be feature complete wrappers,
but to demontrate different use-cases of **snug**.

Requirements
------------

To keep the examples simple, they target python 3.6,
and make use of external libraries.
These can be found in ``requirements/examples.txt``.

List of examples
----------------

* **github**: wrapper for the github REST v3 API. This example illustrates:

    - REST API
    - loading JSON data
    - decorator composition
    - nested queries

* **ns**: wrapper for the NS (dutch railways) API. This example illustrates:

    - REST API
    - loading XML data
    - decorator composition

* **slack**: wrapper for the slack web API. This example illustrates:

    - RPC-style API
    - loading JSON data
    - decorator composition
    - customized authentication
    - queries accross different modules
    - pagination
