from typing import Any


class ExporterBinary:
    def __init__(self, filename: str) -> None:
        self.filename = filename

    def export(self, data: Any) -> None:
        with open(self.filename, "wb") as f:
            f.write(data)
