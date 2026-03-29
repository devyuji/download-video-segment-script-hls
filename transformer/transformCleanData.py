from exporter.exporter import Exporter


class TransformCleanData:
    def transform(self, data: bytes, exporter: Exporter) -> None:
        max_length = min(len(data), 2040)

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
                    print("Found clear data.")

                    cleaned_data = data[i:]

                    exporter.export(cleaned_data)

                    break
