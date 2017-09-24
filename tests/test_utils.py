import pytest

from snug import utils
from dataclasses import dataclass


class TestOnlyOne:

    def test_ok(self):
        assert utils.onlyone([1]) == 1

    def test_too_many(self):
        with pytest.raises(ValueError, match='expected 1'):
            utils.onlyone([1, 2])

    def test_too_few(self):
        with pytest.raises(ValueError, match='expected 1'):
            utils.onlyone([])


def test_replace():

    @dataclass
    class Comment:
        title: str
        body: str

    comment = Comment('my comment', 'blabla')
    newcomment = utils.replace(comment, body='actual comment')
    assert newcomment == Comment('my comment', 'actual comment')
