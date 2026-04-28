from pydantic import BaseModel


class Segment(BaseModel):
    url: str
    index: int

    def __post_init__(self):
        self.url = self.url.strip()


class Decode(BaseModel):
    urls: list[Segment]
    is_encrypted: bool = False
    key: bytes = b""
