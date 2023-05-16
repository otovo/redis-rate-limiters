import asyncio
import logging
import re
from datetime import datetime
from uuid import uuid4

import pytest
from pydantic import ValidationError

from limiters import MaxSleepExceededError
from tests.conftest import delta_to_seconds, run
from tests.token_bucket.conftest import async_tokenbucket_factory

logger = logging.getLogger(__name__)


@pytest.mark.parametrize(
    'n, frequency, timeout',
    [
        (10, 0.1, 1),
        (2, 1, 2),
    ],
)
async def test_token_bucket_runtimes(n, frequency, timeout):
    # Ensure n tasks never complete in less than n/(refill_frequency * refill_amount)
    name = f'runtimes-{uuid4()}'
    tasks = [
        asyncio.create_task(
            run(async_tokenbucket_factory(name=name, capacity=1, refill_frequency=frequency), duration=0)
        )
        for _ in range(n)
    ]

    before = datetime.now()
    await asyncio.gather(*tasks)
    assert timeout <= delta_to_seconds(datetime.now() - before)


async def test_sleep_is_non_blocking():
    async def _sleep(duration: float) -> None:
        await asyncio.sleep(duration)

    tasks = [
        # Create task for token bucket to sleep 1 second
        # And create other tasks to normal asyncio sleep for 1 second
        asyncio.create_task(_sleep(1)),
        asyncio.create_task(run(async_tokenbucket_factory(), 0)),
        asyncio.create_task(_sleep(1)),
        asyncio.create_task(run(async_tokenbucket_factory(), 0)),
    ]

    # Both tasks should complete in ~1 second if thing are working correctly
    await asyncio.wait_for(timeout=1.1, fut=asyncio.gather(*tasks))


def test_repr():
    tb = async_tokenbucket_factory(name='test', capacity=1)()
    assert re.match(r'Token bucket instance for queue {limiter}:token-bucket:test', str(tb))


@pytest.mark.parametrize(
    'config,e',
    [
        ({'name': ''}, None),
        ({'name': None}, ValidationError),
        ({'name': 1}, None),
        ({'name': True}, None),
        ({'capacity': 2}, None),
        ({'capacity': 2.2}, None),
        ({'capacity': -1}, ValidationError),
        ({'capacity': None}, ValidationError),
        ({'capacity': 'test'}, ValidationError),
        ({'refill_frequency': 2.2}, None),
        ({'refill_frequency': 'test'}, ValidationError),
        ({'refill_frequency': None}, ValidationError),
        ({'refill_frequency': -1}, ValueError),
        ({'refill_amount': 1}, None),
        ({'refill_amount': -1}, ValidationError),
        ({'refill_amount': 'test'}, ValidationError),
        ({'refill_amount': None}, ValidationError),
        ({'connection': 'test'}, ValidationError),
        ({'connection': None}, ValidationError),
        ({'max_sleep': 20}, None),
        ({'max_sleep': 0}, None),
        ({'max_sleep': 'test'}, ValidationError),
        ({'max_sleep': None}, ValidationError),
    ],
)
def test_init_types(config, e):
    if e:
        with pytest.raises(e):
            async_tokenbucket_factory(**config)()
    else:
        async_tokenbucket_factory(**config)()


async def test_max_sleep():
    name = uuid4().hex[:6]
    e = (
        r'Scheduled to sleep \`[0-9].[0-9]+\` seconds. This exceeds the maximum accepted sleep time of \`1\.0\`'
        r' seconds.'
    )
    with pytest.raises(MaxSleepExceededError, match=e):
        await asyncio.gather(
            *[asyncio.create_task(run(async_tokenbucket_factory(name=name, max_sleep=1), 0)) for _ in range(10)]
        )
