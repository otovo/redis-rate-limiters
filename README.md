# Limiters

A library for regulating traffic with respect to concurrency or time. It Implements a [semaphore](#semaphore) and [token bucket](#token-bucket).

The data structures are distributed, using Redis, and leverage Lua scripts to reduce latency.
Implements both async and sync implementations.

Compatible with redis-clusters. Currently only supports Python 3.11, but adding support for other versions would be trivial.

## Installation

```
pip install limiters
```

## Semaphore

The semaphore classes are useful when working with concurrency-based
rate limits. Say, e.g., you're allowed 5 active requests at the time
for a given API token.

On trying to acquire the Semaphore, beware that the client will block
until the Semaphore is acquired, or the `max_sleep` limit is exceeded.

If the `max_sleep` limit is exceeded, a `MaxSleepExceededError` is raised.

Here's how you might use the async version:

```python
import asyncio

from httpx import AsyncClient

from limiters import AsyncSemaphore

limiter = AsyncSemaphore(
    name="foo",    # name of the resource you are limiting traffic for
    capacity=5,    # allow 5 concurrent requests
    max_sleep=30,  # raise an error if it takes longer than 30 seconds to acquire the semaphore
    expiry=30      # set expiry on the semaphore keys in Redis to prevent deadlocks
)


async def get_foo():
    async with AsyncClient() as client:
        async with limiter:
            client.get(...)


async def main():
    await asyncio.gather(
        get_foo() for i in range(100)
    )
```

and here is how you might use the sync version:

```python
import requests

from limiters import SyncSemaphore

limiter = SyncSemaphore(
    name="foo",
    capacity=5,
    max_sleep=30,
    expiry=30
)


def main():
    with limiter:
        requests.get(...)
```

## Token bucket

The `TocketBucket` classes are useful if you're working with time-based
rate limits. Say, you are allowed 100 requests per minute, for a given API token.

If the `max_sleep` limit is exceeded, a `MaxSleepExceededError` is raised.

Here's how you might use the async version:

```python
import asyncio

from httpx import AsyncClient

from limiters import AsyncTokenBucket

limiter = AsyncTokenBucket(
    name="foo",          # name of the resource you are limiting traffic for
    capacity=5,          # hold up to 5 tokens
    refill_frequency=1,  # add tokens every second
    refill_amount=1,     # add 1 token when refilling
    max_sleep=30,        # raise an error there are no free tokens for 30 seconds
)


async def get_foo():
    async with AsyncClient() as client:
        async with limiter:
            client.get(...)


async def main():
    await asyncio.gather(
        get_foo() for i in range(100)
    )
```

and here is how you might use the sync version:

```python
import requests

from limiters import SyncTokenBucket

limiter = SyncTokenBucket(
    name="foo",
    capacity=5,
    refill_frequency=1,
    refill_amount=1,
    max_sleep=30,
)


def main():
    with limiter:
        requests.get(...)
```

## Contributing

Contributions are very welcome. Here's how to get started:

- Set up a Python 3.11+ venv, and `pip install poetry`
- Install dependencies with `poetry install`
- Run `pre-commit install` to set up pre-commit
- Run `docker compose up` to run Redis (or run Redis for tests some other way)
- Make your code changes, with tests
- Commit your changes and open a PR
