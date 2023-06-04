import asyncio
import logging
from functools import partial
from pathlib import Path
from typing import TYPE_CHECKING
from uuid import uuid4

from redis.asyncio import Redis as AsyncRedis
from redis.asyncio.cluster import RedisCluster as AsyncRedisCluster
from redis.client import Redis as SyncRedis
from redis.cluster import RedisCluster as SyncRedisCluster

from limiters import AsyncSemaphore, AsyncTokenBucket, SyncSemaphore, SyncTokenBucket

if TYPE_CHECKING:
    from datetime import timedelta

logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).parent.parent

STANDALONE_URL = 'redis://127.0.0.1:6378'
CLUSTER_URL = 'redis://127.0.0.1:6379'

STANDALONE_SYNC_CONNECTION = partial(SyncRedis.from_url, STANDALONE_URL)
CLUSTER_SYNC_CONNECTION = partial(SyncRedisCluster.from_url, CLUSTER_URL)
STANDALONE_ASYNC_CONNECTION = partial(AsyncRedis.from_url, STANDALONE_URL)
CLUSTER_ASYNC_CONNECTION = partial(AsyncRedisCluster.from_url, CLUSTER_URL)

SYNC_CONNECTIONS = [STANDALONE_SYNC_CONNECTION, CLUSTER_SYNC_CONNECTION]
ASYNC_CONNECTIONS = [STANDALONE_ASYNC_CONNECTION, CLUSTER_ASYNC_CONNECTION]


def delta_to_seconds(t: 'timedelta') -> float:
    return t.seconds + t.microseconds / 1_000_000


async def run(pt: AsyncSemaphore | AsyncTokenBucket, sleep_duration: float) -> None:
    async with pt:
        await asyncio.sleep(sleep_duration)


def get_tokenbucket_defaults():
    return {
        'name': uuid4().hex[:6],
        'capacity': 1,
        'refill_frequency': 1.0,
        'refill_amount': 1,
    }


def sync_tokenbucket_factory(*, connection: SyncRedis | SyncRedisCluster, **kwargs) -> SyncTokenBucket:
    return SyncTokenBucket(connection=connection, **(get_tokenbucket_defaults() | kwargs))


def async_tokenbucket_factory(*, connection: AsyncRedis | AsyncRedisCluster, **kwargs) -> AsyncTokenBucket:
    return AsyncTokenBucket(connection=connection, **(get_tokenbucket_defaults() | kwargs))


def get_semaphore_defaults():
    return {
        'name': uuid4().hex[:6],
        'capacity': 1,
    }


def sync_semaphore_factory(*, connection: SyncRedis | SyncRedisCluster, **kwargs) -> SyncSemaphore:
    return SyncSemaphore(connection=connection, **(get_semaphore_defaults() | kwargs))


def async_semaphore_factory(*, connection: AsyncRedis | AsyncRedisCluster, **kwargs) -> AsyncSemaphore:
    return AsyncSemaphore(connection=connection, **(get_semaphore_defaults() | kwargs))
