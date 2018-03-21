"""common logic for all queries"""
import json
from functools import partial, singledispatch
from operator import itemgetter

import snug
from gentools import (compose, map_yield, map_send, oneyield, reusable,
                      map_return)

from .load import registry

API_URL = 'https://slack.com/api/'


class ApiError(Exception):
    pass


def _parse_content(response):
    """parse the response body as JSON, raise on errors"""
    if response.status_code != 200:
        raise ApiError(f'unknown error: {response.content.decode()}')
    result = json.loads(response.content)
    if not result['ok']:
        raise ApiError(f'{result["error"]}: {result.get("detail")}')
    return result


basic_interaction = compose(map_yield(snug.prefix_adder(API_URL)),
                            map_send(_parse_content))
"""basic request/response parsing"""


@singledispatch
def _dump_queryparam_value(val):
    return str(val)


@_dump_queryparam_value.register(bool)
def _dump_bool_value(val):
    return 'true' if val else 'false'


def _dump_params(params):
    return {k: _dump_queryparam_value(v) for k, v in params.items()
            if v is not None}


def paginated_retrieval(methodname, itemtype):
    """decorator factory for retrieval queries from query params"""
    return compose(
        reusable,
        basic_interaction,
        map_yield(partial(_params_as_get, methodname)),
    )


def _params_as_get(methodname: str, params: dict) -> snug.Request:
    return snug.GET(methodname, params=_dump_params(params))


def json_post(methodname, rtype, key):
    """decorator factory for json POST queries"""
    return compose(
        reusable,
        map_return(registry(rtype), itemgetter(key)),
        basic_interaction,
        map_yield(partial(_json_as_post, methodname)),
        oneyield,
    )


def _json_as_post(methodname: str, body: dict) -> snug.Request:
    return snug.POST(methodname,
                     json.dumps({k: v for k, v in body.items()
                                 if v is not None}),
                     headers={'Content-Type': 'application/json'})
