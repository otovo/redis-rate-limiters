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
        (SyncRedisCluster, 6379, [SyncSemaphore, SyncTokenBucket]),
        (AsyncRedis, 6378, [AsyncSemaphore, AsyncTokenBucket]),
        (AsyncRedisCluster, 6379, [AsyncSemaphore, AsyncTokenBucket]),
    ],
)
def test_redis_cluster(klass, port, limiters):
    connection = klass.from_url(f'redis://127.0.0.1:{port}')
    connection.get('INFO')

    for limiter in limiters:
        limiter(
            name='test',
            capacity=99,
            max_sleep=99,
            expiry=99,
            refill_frequency=99,
            refill_amount=99,
            connection=connection,
        )
