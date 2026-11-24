from typing import Any
from pydantic import BaseModel, field_serializer, field_validator

type Header = dict[str, Any]


class Segment(BaseModel):
    url: str
    index: int

    def __post_init__(self):
        self.url = self.url.strip()


class Decode(BaseModel):
    urls: list[Segment]
    is_encrypted: bool = False
    key: bytes = b""
    media_sequence: int = 0
    iv: bytes | None = None

    @field_serializer("key")
    def serialize_key(self, key: bytes) -> str:
        return key.hex()

    @field_validator("key", mode="before")
    @classmethod
    def validate_key(cls, value):
        if isinstance(value, str):
            # Convert the hex string back into raw bytes
            return bytes.fromhex(value)
        return value
