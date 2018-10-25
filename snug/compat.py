"""python 2/3 compatible imports"""
import sys
from operator import attrgetter

PY3 = sys.version_info > (3, )
HAS_PEP492 = sys.version_info > (3, 5, 2)


if PY3:
    import urllib.request as urllib_request
    event_loop = __import__('asyncio').get_event_loop()
    from functools import singledispatch
    from urllib.parse import urlencode
    from urllib.error import HTTPError as urllib_http_error_cls

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
    urllib_http_error_cls = urllib_request.HTTPError  # noqa

    def set_urllib_method(req, method):
        req.get_method = lambda: method
