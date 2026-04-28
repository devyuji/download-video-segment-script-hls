from exporter.exporter import Exporter


class TransformCleanData:
    def transform(self, data: bytes, exporter: Exporter, index: int = 0) -> None:
        max_length = min(len(data), 2040)

        found = False

        VIDEO_BYTE = 0x47

        for i in range(max_length):
            if data[i] == VIDEO_BYTE:
                if (
                    i + 188 < len(data)
                    and data[i + 188] == VIDEO_BYTE
                    and i + 376 < len(data)
                    and data[i + 376] == VIDEO_BYTE
                ):
                    # Slice the bytes object to drop the fake header
                    print(f"Found clear data - {index}")

                    cleaned_data = data[i:]

                    exporter.export(cleaned_data)
                    found = True

                    break

        if not found:
            raise ValueError(f"cleared.data.not.found - {index}")
