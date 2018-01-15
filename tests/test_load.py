import typing as t
from datetime import datetime, timezone, timedelta
from operator import itemgetter

import pytest
from dataclasses import dataclass

from snug import load
from snug.utils import compose, identity


@dataclass(frozen=True)
class User:
    """an example dataclass"""
    id:          int
    name:        str
    hobbies:     t.Optional[t.List[str]]
    nicknames:   t.Set[str]
    height:      float
    likes_pizza: t.Optional[bool] = True


@pytest.fixture
def registry():
    return load.PrimitiveRegistry({
        int:        int,
        float:      float,
        bool:       {'true': True, 'false': False}.__getitem__,
        str:        str,
        type(None): identity,
        object:     identity,
        datetime:   load.parse_iso8601,
    }) | load.GenericRegistry({
        t.List:  load.list_loader,
        t.Set:   load.set_loader,
    }) | load.get_optional_loader


def test_list_loader():
    assert load.list_loader((int, ), [4, '3', '-1']) == [4, 3, -1]


def test_set_loader():
    assert load.set_loader((int, ), [4, '3', '-1']) == {4, 3, -1}


def test_lookup_default():
    getter = load.lookup_defaults(itemgetter('foo'), 'bla')
    assert getter({}) == 'bla'
    assert getter({'foo': 4}) == 4


def test_create_dataclass_loader(registry):
    dloader = load.create_dataclass_loader(User, registry, {
        'id':          itemgetter('id'),
        'name':        itemgetter('username'),
        'likes_pizza': itemgetter('pizza'),
        'height':      itemgetter('height'),
        'nicknames':   itemgetter('nicknames'),
        'hobbies':     itemgetter('hobbies'),
    })
    assert dloader({
        'id': 98,
        'username': 'wilma',
        'hobbies': ['tennis', 'diving'],
        'pizza': 'true',
        'height': 1.64,
        'nicknames': []
    }) == User(98, 'wilma', hobbies=['tennis', 'diving'],
               likes_pizza=True, height=1.64, nicknames=set())


class TestPrimitiveRegistry:

    def test_found(self):
        registry = load.PrimitiveRegistry({int: round})
        loader = registry(int)
        assert loader(3.4) == 3

    def test_not_found(self):
        registry = load.PrimitiveRegistry({int: round})
        with pytest.raises(load.UnsupportedType):
            registry(str)


class TestGenericRegistry:

    def test_ok(self):

        @dataclass(frozen=True)
        class Tag:
            name: str

        registry = load.GenericRegistry({
            t.List: load.list_loader,
        }) | load.PrimitiveRegistry({
            Tag: compose(Tag, '<{}>'.format),
        })

        # simple case
        loader = registry(t.List[Tag])
        assert loader(['hello', 5, 'there']) == [
            Tag('<hello>'), Tag('<5>'), Tag('<there>')
        ]

        # recursive case
        loader = registry(t.List[t.List[Tag]])
        assert loader([
            ['hello', 9, 'there'],
            [],
            ['another', 'list']
        ]) == [
            [Tag('<hello>'), Tag('<9>'), Tag('<there>')],
            [],
            [Tag('<another>'), Tag('<list>')]
        ]

    def test_unsupported_type(self):

        @dataclass(frozen=True)
        class Tag:
            name: str

        registry = load.GenericRegistry({
            t.List: load.list_loader,
        }) | load.PrimitiveRegistry({
            Tag: compose(Tag, '<{}>'.format),
        })
        with pytest.raises(load.UnsupportedType):
            registry(t.Set[Tag])

        with pytest.raises(load.UnsupportedType):
            registry(t.List[str])

        with pytest.raises(load.UnsupportedType):
            registry(object)


class TestGetOptionalLoader:

    def test_ok(self):

        @dataclass(frozen=True)
        class Tag:
            name: str

        registry = load.PrimitiveRegistry({
            Tag: compose(Tag, '<{}>'.format)
        }) | load.get_optional_loader

        loader = registry(t.Optional[Tag])
        assert loader(None) is None
        assert loader(5) == Tag('<5>')


class TestAutoDataclassRegistry:

    def test_ok(self, registry):

        @dataclass
        class Post:
            title: str
            posted_at:  datetime

        registry |= load.AutoDataclassRegistry()
        loader = registry(Post)

        data = {
            'title':     'hello',
            'posted_at': '2017-10-18T14:13:05Z'
        }
        assert loader(data) == Post(
            'hello',
            datetime(2017, 10, 18, 14, 13, 5))

    def test_not_supported(self, registry):

        class MyClass():
            pass

        registry |= load.AutoDataclassRegistry()

        with pytest.raises(load.UnsupportedType):
            registry(MyClass)


def test_dataclass_registry(registry):

    @dataclass
    class Post:
        title:     str
        posted_at: datetime
        author_id: int

    data = {
        'Title':     'hello',
        'date':      '2017-10-18T14:13:05Z',
        'author_id': 12,
    }

    registry |= load.DataclassRegistry({
        Post: {
            'title':     itemgetter('Title'),
            'posted_at': itemgetter('date'),
            'author_id': itemgetter('author_id'),
        }
    })

    loader = registry(Post)

    assert loader(data) == Post(
        'hello',
        datetime(2017, 10, 18, 14, 13, 5),
        author_id=12)

    with pytest.raises(load.UnsupportedType):
        registry(User)


def test_simple_registry():

    @dataclass
    class User:
        name:     str
        id:       int
        nickname: t.Optional[str]

    @dataclass
    class Post:
        title:     str
        user:      User
        comments:  t.List[str]

    loader = load.simple_registry(Post)

    loaded = loader({
        'title': 'hello',
        'comments': ['first!', 'another comment', 5],
        'user': {
            'name': 'bob',
            'nickname': 'bobby',
            'id': '543',
            'extra data': '...',
        }
    })
    assert loaded == Post(
        title='hello',
        comments=['first!', 'another comment', '5'],
        user=User(
            name='bob',
            id=543,
            nickname='bobby'
        )
    )


class TestParseIso8601:

    def test_with_timezone(self):
        parsed = load.parse_iso8601('2012-02-27T13:08:00+0100')
        assert parsed == datetime(
            2012, 2, 27, 13, 8,
            tzinfo=timezone(timedelta(hours=1)))

    def test_no_timezone(self):
        parsed = load.parse_iso8601('2014-06-10T17:25:29Z')
        assert parsed == datetime(2014, 6, 10, 17, 25, 29)
