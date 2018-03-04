"""python 2/3 compatible imports"""
import sys
from operator import attrgetter

PY3 = sys.version_info > (3, )


if PY3:
    import urllib.request as urllib_request
    event_loop = __import__('asyncio').get_event_loop()
    from functools import singledispatch
    from urllib.parse import urlencode

    def set_urllib_method(req, method):
        req.method = method

    def func_from_method(method):
        return method
else:  # pragma: no cover
    import urllib2 as urllib_request  # noqa
    from singledispatch import singledispatch  # noqa
    event_loop = None  # noqa
    from urllib import urlencode  # noqa
    func_from_method = attrgetter('im_func')

    def set_urllib_method(req, method):
        req.get_method = lambda: method
