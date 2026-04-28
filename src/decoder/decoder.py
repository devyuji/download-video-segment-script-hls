from typing import Protocol
from type import Decode


class Decoder(Protocol):
    async def decode(self) -> Decode: ...
