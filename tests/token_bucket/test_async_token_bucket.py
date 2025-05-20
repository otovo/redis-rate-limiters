import asyncio
import logging
import re
from datetime import datetime
from uuid import uuid4

import pytest

from limiters import AsyncTokenBucket, MaxSleepExceededError
from tests.conftest import (
    ASYNC_CONNECTIONS,
    STANDALONE_ASYNC_CONNECTION,
    async_tokenbucket_factory,
    delta_to_seconds,
    run,
)

logger = logging.getLogger(__name__)


@pytest.mark.parametrize('connection', ASYNC_CONNECTIONS)
@pytest.mark.parametrize(
    'n, frequency, timeout',
    [
        (10, 0.1, 1),
        (2, 1, 2),
    ],
)
async def test_token_bucket_runtimes(connection, n, frequency, timeout):
    connection = connection()
    # Ensure n tasks never complete in less than n/(refill_frequency * refill_amount)
    name = f'runtimes-{uuid4()}'
    tasks = [
        asyncio.create_task(
            run(
                async_tokenbucket_factory(connection=connection, name=name, capacity=1, refill_frequency=frequency),
                sleep_duration=0,
            )
        )
        for _ in range(n + 1)  # one added to account for initial capacity of 1
    ]

    before = datetime.now()
    await asyncio.gather(*tasks)
    elapsed = delta_to_seconds(datetime.now() - before)
    assert abs(timeout - elapsed) <= 0.01


@pytest.mark.parametrize('connection', [STANDALONE_ASYNC_CONNECTION])
async def test_sleep_is_non_blocking(connection):
    async def _sleep(sleep_duration: float) -> None:
        await asyncio.sleep(sleep_duration)

    # Create a bucket with 2 slots available
    bucket: AsyncTokenBucket = async_tokenbucket_factory(connection=connection(), capacity=2, refill_amount=2)

    tasks = [
        # Create four tasks for token bucket to sleep 1 second
        # Since the capacity is 2, and the refill amount is two,
        # we expect one second to pass before there are any tokens in the bucket
        # next, we expect the first two token bucket runs to block for one second,
        # then the third and fourth to block for one more; 3 in total
        # We sprinkle in other asyncio sleeps to make sure this is non-blocking
        asyncio.create_task(run(bucket, sleep_duration=1)),
        asyncio.create_task(_sleep(sleep_duration=1)),
        asyncio.create_task(run(bucket, sleep_duration=1)),
        asyncio.create_task(_sleep(sleep_duration=1)),
        asyncio.create_task(run(bucket, sleep_duration=1)),
        asyncio.create_task(_sleep(sleep_duration=1)),
        asyncio.create_task(run(bucket, sleep_duration=1)),
        asyncio.create_task(_sleep(sleep_duration=1)),
    ]

    # Both tasks should complete in ~1 second if thing are working correctly
    await asyncio.wait_for(timeout=3.2, fut=asyncio.gather(*tasks))


@pytest.mark.parametrize('connection', ASYNC_CONNECTIONS)
def test_repr(connection):
    tb = async_tokenbucket_factory(connection=connection(), name='test', capacity=1)
    assert re.match(r'Token bucket instance for queue {limiter}:token-bucket:test', str(tb))


@pytest.mark.parametrize('connection', ASYNC_CONNECTIONS)
@pytest.mark.parametrize(
    'config,error',
    [
        ({'name': ''}, None),
        ({'name': None}, ValueError),
        ({'name': 1}, None),
        ({'name': True}, None),
        ({'capacity': 2}, None),
        ({'capacity': 2.2}, None),
        ({'capacity': -1}, ValueError),
        ({'capacity': None}, ValueError),
        ({'capacity': 'test'}, ValueError),
        ({'refill_frequency': 2.2}, None),
        ({'refill_frequency': 'test'}, ValueError),
        ({'refill_frequency': None}, ValueError),
        ({'refill_frequency': -1}, ValueError),
        ({'refill_amount': 1}, None),
        ({'refill_amount': -1}, ValueError),
        ({'refill_amount': 'test'}, ValueError),
        ({'refill_amount': None}, ValueError),
        ({'max_sleep': 20}, None),
        ({'max_sleep': 0}, None),
        ({'max_sleep': 'test'}, ValueError),
        ({'max_sleep': None}, ValueError),
    ],
)
def test_init_types(connection, config, error):
    if error:
        with pytest.raises(error):
            async_tokenbucket_factory(connection=connection(), **config)
    else:
        async_tokenbucket_factory(connection=connection(), **config)


@pytest.mark.filterwarnings('ignore::RuntimeWarning')
@pytest.mark.parametrize('connection', ASYNC_CONNECTIONS)
async def test_max_sleep(connection):
    connection = connection()
    name = uuid4().hex[:6]
    e = (
        r'Scheduled to sleep \`[0-9].[0-9]+\` seconds. This exceeds the maximum accepted sleep time of \`1\.0\`'
        r' seconds.'
    )
    with pytest.raises(MaxSleepExceededError, match=e):
        await asyncio.gather(
            *[
                asyncio.create_task(run(async_tokenbucket_factory(connection=connection, name=name, max_sleep=1), 0))
                for _ in range(10)
            ]
        )
