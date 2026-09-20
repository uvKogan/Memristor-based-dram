import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))


def pytest_configure(config):
    config.addinivalue_line(
        "markers",
        "slow: test that takes more than a few seconds; deselected by default "
        "via the -m filter in pytest.ini, run with -m slow or -m ''")
