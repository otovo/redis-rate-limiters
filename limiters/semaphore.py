import logging
from datetime import datetime
from types import TracebackType
from typing import TYPE_CHECKING, ClassVar

from pydantic import Field
from redis import Redis as SyncRedis
from redis.asyncio import Redis as AsyncRedis
from redis.commands.core import AsyncScript, Script

from limiters import MaxSleepExceededError
from limiters.base import LuaScriptBase

logger = logging.getLogger(__name__)


class SemaphoreBase(LuaScriptBase):
    name: str
    capacity: int = Field(gt=0)
    max_sleep: float = Field(ge=0, default=0.0)
    expiry: int | None = None

    script_name: ClassVar[str] = 'semaphore.lua'

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


class SyncSemaphore(SemaphoreBase):
    if TYPE_CHECKING:
        connection: SyncRedis[str]
        script: Script

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
        if self.expiry:
            pipeline = self.connection.pipeline()
            # Return capacity to the semaphore
            pipeline.lpush(self.key, 1)
            # Set expiry to prevent deadlocks
            pipeline.expire(self.key, self.expiry)
            pipeline.expire(self.exists, self.expiry)
            pipeline.execute()
        else:
            self.connection.lpush(self.key, 1)

        logger.debug('Released semaphore')


class AsyncSemaphore(SemaphoreBase):
    if TYPE_CHECKING:
        connection: AsyncRedis[str]
        script: AsyncScript

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
        await self.connection.blpop(self.key, self.max_sleep)

        # Raise an exception if we waited too long
        if 0.0 < self.max_sleep < (datetime.now() - start).total_seconds():
            raise MaxSleepExceededError(f'Max sleep ({self.max_sleep}s) exceeded waiting for Semaphore')

        logger.debug('Acquired semaphore %s', self.name)

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        if self.expiry:
            pipeline = self.connection.pipeline()
            # Return capacity to the semaphore
            pipeline.lpush(self.key, 1)
            # Set expiry to prevent deadlocks
            pipeline.expire(self.key, self.expiry)
            pipeline.expire(self.exists, self.expiry)
            await pipeline.execute()
        else:
            await self.connection.lpush(self.key, 1)

        logger.debug('Released semaphore')
