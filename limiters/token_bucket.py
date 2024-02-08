import asyncio
import logging
import time
from datetime import datetime
from types import TracebackType
from typing import ClassVar

from pydantic import BaseModel, Field

from limiters import MaxSleepExceededError
from limiters.base import AsyncLuaScriptBase, SyncLuaScriptBase

logger = logging.getLogger(__name__)


def create_redis_time_tuple() -> tuple[int, int]:
    """
    Create a tuple of two integers representing the current time in seconds and microseconds.

    This mimmicks the TIME command in Redis, which returns the current time in seconds and microseconds.
    See: https://redis.io/commands/time/
    """
    now = time.time()
    seconds_part = int(now)
    microseconds_part = int((now - seconds_part) * 1_000_000)
    return seconds_part, microseconds_part


class TokenBucketBase(BaseModel):
    name: str
    capacity: int = Field(gt=0)
    refill_frequency: float = Field(gt=0)
    refill_amount: int = Field(gt=0)
    max_sleep: float = Field(ge=0, default=0.0)

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
                f'This exceeds the maximum accepted sleep time of `{self.max_sleep}` seconds for {self.name}.'
            )

        logger.info('Sleeping %s seconds (%s)', sleep_time, self.name)
        return sleep_time

    @property
    def key(self) -> str:
        return f'{{limiter}}:token-bucket:{self.name}'

    def __str__(self) -> str:
        return f'Token bucket instance for queue {self.key}'


class SyncTokenBucket(TokenBucketBase, SyncLuaScriptBase):
    script_name: ClassVar[str] = 'token_bucket.lua'

    def __enter__(self) -> float:
        """
        Call the token bucket Lua script, receive a datetime for
        when to wake up, then sleep up until that point in time.
        """

        # Retrieve timestamp for when to wake up from Redis
        seconds, microseconds = create_redis_time_tuple()
        timestamp: int = self.script(
            keys=[self.key],
            args=[self.capacity, self.refill_amount, self.refill_frequency, seconds, microseconds],
        )

        # Estimate sleep time
        sleep_time = self.parse_timestamp(timestamp)

        # Sleep before returning
        time.sleep(sleep_time)

        return sleep_time

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        return


class AsyncTokenBucket(TokenBucketBase, AsyncLuaScriptBase):
    script_name: ClassVar[str] = 'token_bucket.lua'

    async def __aenter__(self) -> None:
        """
        Call the token bucket Lua script, receive a datetime for
        when to wake up, then sleep up until that point in time.
        """

        # Retrieve timestamp for when to wake up from Redis
        seconds, microseconds = create_redis_time_tuple()
        timestamp = await self.script(
            keys=[self.key],
            args=[self.capacity, self.refill_amount, self.refill_frequency, seconds, microseconds],
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
