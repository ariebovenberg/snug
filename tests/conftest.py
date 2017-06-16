import pytest

import omgorm as orm


@pytest.fixture
def SessionSubclass():
    class MySiteSession(orm.Session):
        pass

    return MySiteSession
