from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, ClassVar

from redis import Redis as SyncRedis
from redis.asyncio import Redis as AsyncRedis
from redis.asyncio.cluster import RedisCluster as AsyncRedisCluster
from redis.cluster import RedisCluster as SyncRedisCluster
from redis.commands.core import AsyncScript, Script


@dataclass
class SyncLuaScriptBase:
    if TYPE_CHECKING:
        connection: SyncRedis[str] | SyncRedisCluster[str]
    else:
        connection: SyncRedis | SyncRedisCluster

    script_name: ClassVar[str]
    script: Script = None  # type: ignore[assignment]

    def __post_init__(self) -> None:
        # Load script on initialization
        with open(Path(__file__).parent / self.script_name) as f:
            self.script = self.connection.register_script(f.read())  # type: ignore[union-attr]


@dataclass
class AsyncLuaScriptBase:
    if TYPE_CHECKING:
        connection: AsyncRedis[str] | AsyncRedisCluster[str]
    else:
        connection: AsyncRedis | AsyncRedisCluster

    script_name: ClassVar[str]
    script: AsyncScript = None  # type: ignore[assignment]

    def __post_init__(self) -> None:
        # Load script on initialization
        with open(Path(__file__).parent / self.script_name) as f:
            self.script = self.connection.register_script(f.read())  # type: ignore[union-attr]
