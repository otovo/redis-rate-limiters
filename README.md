# Redis rate limiters

A library for regulating traffic with respect to concurrency or time.
It sync and async context managers for a [semaphore](#semaphore)- and a [token bucket](#token-bucket)
implementation.

The rate limiting implementations are distributed, using Redis,
and leverages Lua scripts to greatly improve performance and simplify the code. Lua scripts
run on the Redis server, and make each implementation fully atomic.

Both implementations are compatible for use with redis-clusters.
We currently only support Python 3.11, but can add support for older versions if needed.

## Installation

```
pip install redis-rate-limiters
```

## Usage

### Semaphore

The semaphore classes are useful when you have concurrency restrictions;
e.g., say you're allowed 5 active requests at the time for a given API token.

Beware that the client will block until the Semaphore is acquired,
or the `max_sleep` limit is exceeded. If the `max_sleep` limit is exceeded, a `MaxSleepExceededError` is raised.

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

### Token bucket

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

### Using them as a decorator

We don't ship decorators in the package, but if you would
like to limit the rate at which a whole function is run,
you can create your own, like this:

```python
from limiters import AsyncSemaphore


# Define a decorator function
def limit(name, capacity):
  def middle(f):
    async def inner(*args, **kwargs):
      async with AsyncSemaphore(name=name, capacity=capacity):
        return await f(*args, **kwargs)
    return inner
  return middle


# Then pass the relevant limiter arguments like this
@limit(name="foo", capacity=5)
def fetch_foo(id: UUID) -> Foo:
```

## Contributing

Contributions are very welcome. Here's how to get started:

- Set up a Python 3.11+ venv, and `pip install poetry`
- Install dependencies with `poetry install`
- Run `pre-commit install` to set up pre-commit
- Run `docker compose up` to run Redis (or run Redis for tests some other way)
- Make your code changes, with tests
- Commit your changes and open a PR

## Publishing a new version

To publish a new version:

- Update the package version in the `pyproject.toml`
- Open [Github releases](https://github.com/otovo/redis-rate-limiters/releases)
- Press "Draft a new release"
- Set a tag matching the new version (for example, `v0.4.2`)
- Set the title matching the tag
- Add some release notes, explaining what has changed
- Publish

Once the release is published, our [publish workflow](https://github.com/otovo/redis-rate-limiters/blob/main/.github/workflows/publish.yaml) should be triggered
to push the new version to PyPI.
