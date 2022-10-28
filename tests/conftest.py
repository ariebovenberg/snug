import pytest


def pytest_addoption(parser):
    parser.addoption(
        "--live",
        action="store_true",
        default=False,
        help="run against live data",
    )


def pytest_collection_modifyitems(config, items):
    if config.getoption("--live"):
        # --live given in cli: do not skip live tests
        return
    skip_live = pytest.mark.skip(reason="need --live option to run")
    for item in items:
        if "live" in item.keywords:
            item.add_marker(skip_live)
