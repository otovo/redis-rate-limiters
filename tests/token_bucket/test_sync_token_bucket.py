import logging
from datetime import datetime, timedelta
from uuid import uuid4

import pytest

from limiters import MaxSleepExceededError
from tests.token_bucket.conftest import sync_tokenbucket_factory

logger = logging.getLogger(__name__)


async def test_sync_token_bucket():
    start = datetime.now()
    for i in range(5):
        with sync_tokenbucket_factory(name=f'{uuid4()}', refill_amount=2, refill_frequency=0.2)():
            ...

    # This has the potential of being flaky if CI is extremely slow
    assert timedelta(seconds=1) < datetime.now() - start < timedelta(seconds=2)


async def test_max_sleep():
    name = uuid4().hex[:6]
    e = (
        r'Scheduled to sleep \`[0-9].[0-9]+\` seconds. This exceeds the maximum accepted sleep time of \`0\.1\`'
        r' seconds.'
    )
    with pytest.raises(MaxSleepExceededError, match=e), sync_tokenbucket_factory(name=name, max_sleep=0.1)():
        ...
