import asyncio
import logging
import time
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


class TokenBucketBase(LuaScriptBase):
    name: str
    capacity: int = Field(gt=0)
    refill_frequency: float = Field(gt=0)
    refill_amount: int = Field(gt=0)
    max_sleep: float = Field(ge=0, default=0.0)

    script_name: ClassVar[str] = 'token_bucket.lua'

    def parse_timestamp(self, timestamp: int) -> float:
        # Parse to datetime
        wake_up_time = datetime.fromtimestamp(timestamp / 1000)

        # Establish the current time, with a very small buffer for processing time
        now = datetime.now()

        # Return if we don't need to sleep
        if wake_up_time < now:
            return 0

        # Establish how long we should sleep
        sleep_time = (wake_up_time - now).total_seconds()

        # Raise an error if we exceed the maximum sleep setting
        if self.max_sleep != 0.0 and sleep_time > self.max_sleep:
            raise MaxSleepExceededError(
                f'Scheduled to sleep `{sleep_time}` seconds. '
                f'This exceeds the maximum accepted sleep time of `{self.max_sleep}` seconds.'
            )

        logger.info('Sleeping %s seconds', sleep_time)
        return sleep_time

    @property
    def key(self) -> str:
        return f'{{limiter}}:token-bucket:{self.name}'

    def __str__(self) -> str:
        return f'Token bucket instance for queue {self.key}'


class SyncTokenBucket(TokenBucketBase):
    if TYPE_CHECKING:
        connection: SyncRedis[str]
        script: Script

    def __enter__(self) -> None:
        """
        Call the token bucket Lua script, receive a datetime for
        when to wake up, then sleep up until that point in time.
        """
        # Retrieve timestamp for when to wake up from Redis
        timestamp: int = self.script(
            keys=[self.key],
            args=[self.capacity, self.refill_amount, self.refill_frequency],
        )

        # Estimate sleep time
        sleep_time = self.parse_timestamp(timestamp)

        # Sleep before returning
        time.sleep(sleep_time)

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        return


class AsyncTokenBucket(TokenBucketBase):
    if TYPE_CHECKING:
        connection: AsyncRedis[str]
        script: AsyncScript

    async def __aenter__(self) -> None:
        """
        Call the token bucket Lua script, receive a datetime for
        when to wake up, then sleep up until that point in time.
        """
        # Retrieve timestamp for when to wake up from Redis
        timestamp = await self.script(
            keys=[self.key],
            args=[self.capacity, self.refill_amount, self.refill_frequency],
        )

        # Estimate sleep time
        sleep_time = self.parse_timestamp(timestamp)

        # Sleep before returning
        await asyncio.sleep(sleep_time)

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        return
