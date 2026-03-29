import json
from typing import Any


class ExportJSONFromDataClass:
    def __init__(self, filename: str) -> None:
        self.filename = filename

    def export(self, data: Any) -> None:
        with open(self.filename, "w") as f:
            clean_dict = data.model_dump(mode="json")
            json.dump(clean_dict, f, indent=4)
