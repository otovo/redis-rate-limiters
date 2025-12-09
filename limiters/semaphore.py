import logging
from dataclasses import dataclass
from datetime import datetime
from types import TracebackType
from typing import TYPE_CHECKING, ClassVar

from redis import Redis as SyncRedis
from redis.asyncio import Redis as AsyncRedis
from redis.asyncio.client import Pipeline
from redis.asyncio.cluster import ClusterPipeline
from redis.asyncio.cluster import RedisCluster as AsyncRedisCluster
from redis.cluster import RedisCluster as SyncRedisCluster

from limiters import MaxSleepExceededError
from limiters.base import AsyncLuaScriptBase, SyncLuaScriptBase

logger = logging.getLogger(__name__)


class SemaphoreBase:
    name: str
    capacity: int
    max_sleep: float
    expiry: int

    def _validate(self) -> None:
        if self.name is None:
            raise ValueError('name must not be None')
        try:
            if self.capacity <= 0:
                raise ValueError('capacity must be > 0')
        except TypeError:
            raise ValueError('capacity must be a number') from None
        try:
            if self.max_sleep < 0:
                raise ValueError('max_sleep must be >= 0')
        except TypeError:
            raise ValueError('max_sleep must be a number') from None

    @property
    def key(self) -> str:
        """Key to use for the Semaphore list."""
        return f'{{limiter}}:semaphore:{self.name}'

    @property
    def exists(self) -> str:
        """Key to use when checking if the Semaphore list has been created or not."""
        return f'{{limiter}}:semaphore:{self.name}-exists'

    def __str__(self) -> str:
        return f'Semaphore instance for queue {self.key}'


@dataclass
class SyncSemaphore(SyncLuaScriptBase, SemaphoreBase):
    if TYPE_CHECKING:
        connection: SyncRedis[str] | SyncRedisCluster[str]
    else:
        connection: SyncRedis | SyncRedisCluster
    name: str
    capacity: int
    max_sleep: float = 0.0
    expiry: int = 30

    script_name: ClassVar[str] = 'semaphore.lua'

    def __post_init__(self) -> None:
        self._validate()
        self._register_script()

    def __enter__(self) -> None:
        """
        Call the semaphore Lua script to create a semaphore, then call BLPOP to acquire it.
        """
        # Retrieve timestamp for when to wake up from Redis
        semaphore_created: bool = self.script(
            keys=[self.key, self.exists],
            args=[self.capacity],
        )

        if semaphore_created:
            logger.info('Created new semaphore `%s` with capacity %s', self.name, self.capacity)
        else:
            logger.debug('Skipped creating semaphore, since one exists')

        start = datetime.now()

        self.connection.blpop(self.key, self.max_sleep)
        pipeline = self.connection.pipeline()
        pipeline.expire(self.key, self.expiry)
        pipeline.expire(self.exists, self.expiry)
        pipeline.execute()

        # Raise an exception if we exceeded `max_sleep`
        if 0.0 < self.max_sleep < (datetime.now() - start).total_seconds():
            raise MaxSleepExceededError('Max sleep exceeded waiting for Semaphore')

        logger.debug('Acquired semaphore %s', self.name)

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        pipeline = self.connection.pipeline()
        pipeline.lpush(self.key, 1)
        pipeline.expire(self.key, self.expiry)
        pipeline.expire(self.exists, self.expiry)
        pipeline.execute()

        logger.debug('Released semaphore %s', self.name)


@dataclass
class AsyncSemaphore(AsyncLuaScriptBase, SemaphoreBase):
    if TYPE_CHECKING:
        connection: AsyncRedis[str] | AsyncRedisCluster[str]
    else:
        connection: AsyncRedis | AsyncRedisCluster
    name: str
    capacity: int
    max_sleep: float = 0.0
    expiry: int = 30

    script_name: ClassVar[str] = 'semaphore.lua'

    def __post_init__(self) -> None:
        self._validate()
        self._register_script()

    async def __aenter__(self) -> None:
        """
        Call the semaphore Lua script to create a semaphore, then call BLPOP to acquire it.
        """
        # Retrieve timestamp for when to wake up from Redis

        if await self.script(
            keys=[self.key, self.exists],
            args=[self.capacity],
        ):
            logger.info('Created new semaphore `%s` with capacity %s', self.name, self.capacity)
        else:
            logger.debug('Skipped creating semaphore, since one exists')

        start = datetime.now()

        await self.connection.blpop(self.key, self.max_sleep)  # type: ignore[union-attr]
        pipeline: Pipeline[str] | ClusterPipeline[str] = self.connection.pipeline()
        pipeline.expire(self.key, self.expiry)  # type: ignore[union-attr]
        pipeline.expire(self.exists, self.expiry)  # type: ignore[union-attr]
        await pipeline.execute()

        # Raise an exception if we waited too long
        if 0.0 < self.max_sleep < (datetime.now() - start).total_seconds():
            raise MaxSleepExceededError(f'Max sleep ({float(self.max_sleep)}s) exceeded waiting for Semaphore')

        logger.debug('Acquired semaphore %s', self.name)

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        pipeline: Pipeline[str] | ClusterPipeline[str] = self.connection.pipeline()
        pipeline.lpush(self.key, 1)  # type: ignore[union-attr]
        pipeline.expire(self.key, self.expiry)  # type: ignore[union-attr]
        pipeline.expire(self.exists, self.expiry)  # type: ignore[union-attr]
        await pipeline.execute()

        logger.debug('Released semaphore %s', self.name)
