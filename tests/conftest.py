import os
import pytest


def pytest_sessionstart(session):
    if os.getenv('CI') and not os.getenv('TEST_DATABASE_URL'):
        raise pytest.UsageError('CI requires TEST_DATABASE_URL; PostgreSQL tests must run')
