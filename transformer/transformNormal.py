from exporter.exporter import Exporter


class TransformNormal:
    def transform(self, data: bytes, exporter: Exporter, index: int = 0) -> None:
        exporter.export(data)
