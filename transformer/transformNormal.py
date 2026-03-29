from exporter.exporter import Exporter


class TransformNormal:
    def transform(self, data: bytes, exporter: Exporter) -> None:
        exporter.export(data)
