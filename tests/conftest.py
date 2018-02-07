def pytest_addoption(parser):
    parser.addoption("--live", action="store_true",
                     default=False, help="run against live data")
