import asyncio
import logging
from functools import partial
from pathlib import Path
from typing import TYPE_CHECKING

import pytest
from redis.asyncio import Redis

if TYPE_CHECKING:
    from datetime import timedelta

logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).parent.parent


def get_connection():
    return Redis.from_url('redis://127.0.0.1:6379')


@pytest.fixture
def connection():
    return get_connection()


def delta_to_seconds(t: 'timedelta') -> float:
    return t.seconds + t.microseconds / 1_000_000


async def run(pt: partial, duration: float) -> None:
    async with pt():
        logger.info('Sleeping %s', duration)
        await asyncio.sleep(duration)
