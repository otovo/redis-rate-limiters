from pathlib import Path
from typing import Any, ClassVar

from pydantic import BaseModel
from redis import Redis as SyncRedis
from redis.asyncio import Redis as AsyncRedis
from redis.commands.core import AsyncScript, Script


class LuaScriptBase(BaseModel):
    connection: SyncRedis | AsyncRedis  # type: ignore[type-arg]
    script_name: ClassVar[str]
    script: Script | AsyncScript = None  # type: ignore

    class Config:
        arbitrary_types_allowed = True

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)

        # Load script on initialization
        with open(Path(__file__).parent / self.script_name) as f:
            self.script = self.connection.register_script(f.read())
