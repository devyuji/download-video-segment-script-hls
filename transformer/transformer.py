from typing import Protocol

from exporter.exporter import Exporter


class Transformer(Protocol):
    def transform(self, data: bytes, exporter: Exporter) -> None: ...
