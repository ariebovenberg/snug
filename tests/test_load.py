import typing as t

import lxml.etree
import pytest
from toolz import compose, partial
from dataclasses import dataclass

from snug import load


@dataclass(frozen=True)
class User:
    """an example dataclass"""
    id:          int
    name:        str
    hobbies:     t.Optional[t.List[str]]
    likes_pizza: t.Optional[bool]
    height:      float
    nicknames:   t.Set[str]


@pytest.fixture
def loaders():
    _loaders = {
        int:   int,
        float: float,
        bool:  {'true': True, 'false': False}.__getitem__,
        str:   str,
    }
    _loaders[t.List] = load.list_

    load.registered_dataclass_loader(User, {
        'id':          'userid',
        'name':        'username',
        'hobbies':     'hobbies',
        'likes_pizza': 'pizza',
        'height':      'h',
        'nicknames':   'nicknames',
    }, loaders=_loaders)

    return _loaders


class TestLoad:

    def test_load_generic(self):

        @dataclass(frozen=True)
        class Tag:
            name: str

        loaders = {Tag: compose(Tag, '<{}>'.format)}
        loaders[t.List] = load.list_

        loaded = load.load(t.List[Tag], ['hello', 5, 'there'], loaders=loaders)
        assert loaded == [Tag('<hello>'), Tag('<5>'), Tag('<there>')]

    def test_load_simple(self):

        @dataclass(frozen=True)
        class Tag:
            name: str

        loaders = {Tag: compose(Tag, '<{}>'.format)}
        assert load.load(Tag, 'foo', loaders=loaders) == Tag('<foo>')


def test_load_list():
    loaders = {int: int}
    assert load.list_((int, ), [4, '3', '-1'], loaders) == [4, 3, -1]


def test_load_optional():
    loader = partial(load.optional, [int, type(None)], loaders={int: int})
    assert loader('4') == 4
    assert loader(3) == 3
    assert loader(3.2) == 3
    assert loader(None) is None


@pytest.mark.parametrize('data, loaded', [
    ({
        'id': 98,
        'username': 'wilma',
        'hobbies': ['tennis', 'diving'],
        'pizza': 'true',
        'height': 1.64,
        'nicknames': []
    },
     User(98, 'wilma', hobbies=['tennis', 'diving'],
          likes_pizza=True, height=1.64, nicknames=[])),
    ({
        'id': '44',
        'username': 'bob',
        'height': '1.85',
        'nicknames': ['bobby'],
    },
     User(44, 'bob', hobbies=None, likes_pizza=None, height=1.85,
          nicknames=['bobby'])
    )
])
def test_registered_dataclass_loader(data, loaded, loaders):

    loader = load.registered_dataclass_loader(User, {
        'id':          'id',
        'name':        'username',
        'hobbies':     'hobbies',
        'likes_pizza': 'pizza',
        'height':      'height',
        'nicknames':   'nicknames'
    }, loaders=loaders)
    assert loaders[User] is loader
    assert loader(data) == loaded


class TestGetitem:

    def test_default(self):

        class MyClass:
            pass

        with pytest.raises(TypeError, match='MyClass'):
            load.getitem(MyClass(), 'foo', multiple=False, optional=False)

    def test_mapping(self):
        my_mapping = {'foo': 4}

        assert load.getitem(my_mapping, 'foo',
                            multiple=False, optional=False) == 4

        with pytest.raises(LookupError, match='blabla'):
            load.getitem(my_mapping, 'blabla',
                         multiple=False, optional=False)

        assert load.getitem(my_mapping, 'bla',
                            multiple=False, optional=True) is None

    def test_xml_elem(self):
        xml = lxml.etree.fromstring('''
        <MyRoot>
          <MyParent>
            <Child1>foo</Child1>
            <Child1>bar</Child1>
          </MyParent>
        </MyRoot>
        ''')
        assert load.getitem(xml, 'MyParent/Child1[1]/text()',
                            multiple=False, optional=False) == 'foo'
        assert load.getitem(
            xml, 'MyParent/Child1/text()',
            multiple=True, optional=False) == ['foo', 'bar']

        with pytest.raises(LookupError, match='blabla'):
            load.getitem(xml, 'MyParent.blabla', multiple=True,
                         optional=False)
