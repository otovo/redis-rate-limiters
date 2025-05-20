import asyncio

import pytest
from redis.asyncio import Redis as AsyncRedis
from redis.asyncio.cluster import RedisCluster as AsyncRedisCluster
from redis.client import Redis as SyncRedis
from redis.cluster import RedisCluster as SyncRedisCluster

from limiters import AsyncSemaphore, AsyncTokenBucket, SyncSemaphore, SyncTokenBucket


@pytest.mark.parametrize(
    'klass,port,limiters',
    [
        (SyncRedis, 6378, [SyncSemaphore, SyncTokenBucket]),
        (SyncRedisCluster, 6380, [SyncSemaphore, SyncTokenBucket]),
        (AsyncRedis, 6378, [AsyncSemaphore, AsyncTokenBucket]),
        (AsyncRedisCluster, 6380, [AsyncSemaphore, AsyncTokenBucket]),
    ],
)
def test_redis_cluster(klass, port, limiters):
    connection = klass.from_url(f'redis://127.0.0.1:{port}')
    if hasattr(connection, '__aenter__'):
        # Async connection
        asyncio.get_event_loop().run_until_complete(connection.get('INFO'))
    else:
        # Sync connection
        connection.get('INFO')

    for limiter in limiters:
        kwargs = {
            'name': 'test',
            'capacity': 99,
            'max_sleep': 99,
            'connection': connection,
        }
        if limiter in (SyncSemaphore, AsyncSemaphore):
            kwargs['expiry'] = 99
        else:
            kwargs['refill_frequency'] = 99
            kwargs['refill_amount'] = 99
        limiter(**kwargs)
