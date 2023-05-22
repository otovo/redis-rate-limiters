import logging
import threading
import time
from datetime import datetime, timedelta
from uuid import uuid4

import pytest

from limiters import MaxSleepExceededError
from tests.semaphore.conftest import sync_semaphore_factory

logger = logging.getLogger(__name__)


async def test_sync_semaphore():
    start = datetime.now()
    for i in range(5):
        with sync_semaphore_factory(name=f'{uuid4()}', capacity=1)():
            time.sleep(0.2)

    # This has the potential of being flaky if CI is extremely slow
    assert timedelta(seconds=1) < datetime.now() - start < timedelta(seconds=2)


def _run(name, sleep):
    with sync_semaphore_factory(name=name, capacity=1, max_sleep=0.1, expiry=1)():
        time.sleep(sleep)


async def test_sync_max_sleep():
    name = uuid4().hex[:6]
    threading.Thread(target=_run, args=(name, 1)).start()
    time.sleep(0.1)
    with pytest.raises(MaxSleepExceededError, match=r'Max sleep exceeded waiting for Semaphore'):
        _run(name, 0)
