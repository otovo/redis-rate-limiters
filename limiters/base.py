from pathlib import Path
from typing import TYPE_CHECKING, Any, ClassVar

from pydantic import BaseModel
from redis import Redis as SyncRedis
from redis.asyncio import Redis as AsyncRedis
from redis.asyncio.cluster import RedisCluster as AsyncRedisCluster
from redis.cluster import RedisCluster as SyncRedisCluster
from redis.commands.core import AsyncScript, Script


class SyncLuaScriptBase(BaseModel):
    if TYPE_CHECKING:
        connection: SyncRedis[str] | SyncRedisCluster[str]
    else:
        connection: SyncRedis | SyncRedisCluster

    script_name: ClassVar[str]
    script: Script = None  # type: ignore[assignment]

    class Config:
        arbitrary_types_allowed = True

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)

        # Load script on initialization
        with open(Path(__file__).parent / self.script_name) as f:
            self.script = self.connection.register_script(f.read())  # type: ignore[union-attr]


class AsyncLuaScriptBase(BaseModel):
    if TYPE_CHECKING:
        connection: AsyncRedis[str] | AsyncRedisCluster[str]
    else:
        connection: AsyncRedis | AsyncRedisCluster

    script_name: ClassVar[str]
    script: AsyncScript = None  # type: ignore[assignment]

    class Config:
        arbitrary_types_allowed = True

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)

        # Load script on initialization
        with open(Path(__file__).parent / self.script_name) as f:
            self.script = self.connection.register_script(f.read())  # type: ignore[union-attr]
