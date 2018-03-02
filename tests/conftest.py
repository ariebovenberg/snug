import asyncio

import pytest


def pytest_addoption(parser):
    parser.addoption("--live", action="store_true",
                     default=False, help="run against live data")


@pytest.fixture
def loop(scope='session'):
    return asyncio.get_event_loop()
