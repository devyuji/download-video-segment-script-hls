from type import Decode


class DecodeFailList:
    def __init__(self, filename) -> None:
        self.filename = filename

    async def decode(self) -> Decode:
        with open(self.filename, "r") as f:
            data = f.read()

            d = Decode.model_validate_json(data)

            return d
