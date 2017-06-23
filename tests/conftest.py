import pytest

import snug


@pytest.fixture
def SessionSubclass():
    class MySiteSession(snug.Session):
        pass

    return MySiteSession
