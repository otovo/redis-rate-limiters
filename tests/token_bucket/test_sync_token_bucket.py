import logging
from datetime import datetime, timedelta
from uuid import uuid4

import pytest

from limiters import MaxSleepExceededError
from tests.conftest import SYNC_CONNECTIONS, sync_tokenbucket_factory

logger = logging.getLogger(__name__)


@pytest.mark.parametrize('connection', SYNC_CONNECTIONS)
async def test_sync_token_bucket(connection):
    start = datetime.now()
    for _ in range(5):
        with sync_tokenbucket_factory(
            connection=connection(), name=f'{uuid4()}', refill_amount=2, refill_frequency=0.2
        ):
            pass

    # This has the potential of being flaky if CI is extremely slow
    assert timedelta(seconds=0) < datetime.now() - start < timedelta(seconds=1)


@pytest.mark.parametrize('connection', SYNC_CONNECTIONS)
async def test_sync_max_sleep(connection):
    name = uuid4().hex[:6]
    e = (
        r'Scheduled to sleep \`[0-9].[0-9]+\` seconds. This exceeds the maximum accepted sleep time of \`0\.1\`'
        r' seconds.'
    )
    with sync_tokenbucket_factory(connection=connection(), name=name, max_sleep=99):
        pass

    with (
        pytest.raises(MaxSleepExceededError, match=e),
        sync_tokenbucket_factory(connection=connection(), name=name, max_sleep=0.1),
    ):
        pass
