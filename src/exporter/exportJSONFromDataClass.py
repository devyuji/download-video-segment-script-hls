from typing import Any


class ExportJSONFromDataClass:
    def __init__(self, filename: str) -> None:
        self.filename = filename

    def export(self, data: Any) -> None:
        with open(self.filename, "w") as f:
            f.write(data.model_dump_json(indent=2))
