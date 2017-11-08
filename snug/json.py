"""utilities for working with JSON data"""
import json
import typing as t

from dataclasses import dataclass


def parse_response(resp):
    return ObjectResponse(resp.status_code,
                          data=json.loads(resp.content),
                          headers=resp.headers)


@dataclass(frozen=True)
class ObjectResponse(t.Mapping[str, t.Any]):
    """a JSON object response"""
    status_code: int
    data:        t.Dict[str, t.Any]
    headers:     t.Dict[str, str]

    def __getitem__(self, key):
        return self.data[key]

    def __iter__(self):
        return iter(self.data)

    def __len__(self):
        return len(self.data)
