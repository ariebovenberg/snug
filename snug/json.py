"""utilities for working with JSON data"""
import json
import typing as t

from .http import Response


def parse_response(resp: Response[bytes]) -> t.Union[Response[list],
                                                     Response[dict]]:
    return Response(resp.status_code,
                    content=json.loads(resp.content),
                    headers=resp.headers)
