import xml.etree.ElementTree as ET

import pytest

from snug import xml

XMLDATA = ET.fromstring('''
<MyRoot foo="3">
    <MyParent>
        <Child1 bla="qux">foo</Child1>
        <Child1> bar  </Child1>
    </MyParent>
</MyRoot>
''')


class TestElemGetter:

    def test_simple(self):
        getter = xml.elemgetter('MyParent/Child1')
        elem = getter(XMLDATA)
        assert elem.text == 'foo'
        assert elem.attrib == {'bla': 'qux'}

    def test_not_found(self):
        getter = xml.elemgetter('MyParent/BlaBla')
        with pytest.raises(LookupError, match='MyParent/BlaBla'):
            getter(XMLDATA)

    @pytest.mark.skip(reason='not implemented')
    def test_default(self):
        getter = xml.elemgetter('MyParent/Blabla', default='bla')
        assert getter(XMLDATA) == 'bla'
        getter = xml.elemgetter('MyParent/Blabla', default=None)
        assert getter(XMLDATA) is None
        getter2 = xml.elemgetter('MyParent', default=None)
        assert getter2(XMLDATA) is not None


class TestElemsGetter:

    def test_simple(self):
        getter = xml.elemsgetter('MyParent/Child1')
        elems = getter(XMLDATA)
        assert len(elems) == 2
        assert [e.text for e in elems] == ['foo', ' bar  ']

    def test_not_found(self):
        getter = xml.elemsgetter('MyParent/Child2')
        assert getter(XMLDATA) == []


class TestTextGetter:

    def test_simple(self):
        getter = xml.textgetter('MyParent/Child1')
        assert getter(XMLDATA) == 'foo'

    def test_not_found(self):
        getter = xml.textgetter('MyParent/Child2')
        with pytest.raises(LookupError, match='MyParent/Child2'):
            getter(XMLDATA)

    def test_default(self):
        getter = xml.textgetter('MyParent/Child2', default=None)
        assert getter(XMLDATA) is None

        getter = xml.textgetter('MyParent/Child1', default=None)
        assert getter(XMLDATA) == 'foo'

    def test_strip(self):
        getter = xml.textgetter('MyParent/Child1[2]', strip=True)
        assert getter(XMLDATA) == 'bar'

    def test_strip_and_default(self):
        getter = xml.textgetter('MyParent/Child2', default=None, strip=True)
        assert getter(XMLDATA) is None


class TestAttribGetter:

    def test_simple(self):
        getter = xml.attribgetter('MyParent/Child1', 'bla')
        assert getter(XMLDATA) == 'qux'

    def test_path_not_found(self):
        getter = xml.attribgetter('MyParent/Child2', 'blabla')
        with pytest.raises(LookupError, match='MyParent/Child2'):
            getter(XMLDATA)

    def test_root_path(self):
        getter = xml.attribgetter('.', 'foo')
        assert getter(XMLDATA) == '3'

    def test_attrib_not_found(self):
        getter = xml.attribgetter('MyParent/Child1', 'foo')
        with pytest.raises(LookupError, match='foo'):
            getter(XMLDATA)

    def test_default(self):
        getter = xml.attribgetter('MyParent/Child1', 'foo', default=None)
        assert getter(XMLDATA) is None

        getter2 = xml.attribgetter('MyParent/Child1', 'bla', default=None)
        assert getter2(XMLDATA) == 'qux'


class TestTextsGetter:

    def test_simple(self):
        getter = xml.textsgetter('MyParent/Child1')
        assert getter(XMLDATA) == ['foo', ' bar  ']

    def test_path_not_found(self):
        getter = xml.textsgetter('MyParent/Child2')
        assert getter(XMLDATA) == []

    def test_strip(self):
        getter = xml.textsgetter('MyParent/Child1', strip=True)
        assert getter(XMLDATA) == ['foo', 'bar']
