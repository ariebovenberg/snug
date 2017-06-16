import pytest

import omgorm as orm


@pytest.fixture
def SessionSubclass():
    class MySiteSession(orm.Session):

        def __init__(self, username, **kwargs):
            self.username = username
            super().__init__(**kwargs)

        def __repr__(self):
            return f'<{self.__class__.__name__}({self.username})>'

    return MySiteSession
