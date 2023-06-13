import logging
import threading
import time
from datetime import datetime, timedelta
from uuid import uuid4

import pytest

from limiters import MaxSleepExceededError
from tests.conftest import SYNC_CONNECTIONS, sync_semaphore_factory

logger = logging.getLogger(__name__)


@pytest.mark.parametrize('connection', SYNC_CONNECTIONS)
async def test_sync_semaphore(connection):
    start = datetime.now()
    for _ in range(5):
        with sync_semaphore_factory(connection=connection(), name=f'{uuid4()}', capacity=1):
            time.sleep(0.2)

    # This has the potential of being flaky if CI is extremely slow
    assert timedelta(seconds=1) < datetime.now() - start < timedelta(seconds=2)


def _run(name, sleep, connection):
    with sync_semaphore_factory(connection=connection, name=name, capacity=1, max_sleep=0.1, expiry=1):
        time.sleep(sleep)


@pytest.mark.parametrize('connection', SYNC_CONNECTIONS)
async def test_sync_max_sleep(connection):
    name = uuid4().hex[:6]
    c = connection()
    threading.Thread(target=_run, args=(name, 1, c)).start()
    time.sleep(0.1)
    with pytest.raises(MaxSleepExceededError, match=r'Max sleep exceeded waiting for Semaphore'):
        _run(name, 0, c)
