import sys
import base64
import os
import asyncio
import aiohttp
import json
import subprocess
from typing import Any
from transformer.tranformFytp import TransformFYTPOrMOOF
from transformer.transformNormal import TransformNormal
from type import Decode, Segment
from decoder import (
    DecodeFailList,
    DecodePartialURLWithInitial,
    Decoder,
    DecodeFullURL,
    DecodePartialURL,
)
from exporter.exporter import Exporter
from transformer.transformer import Transformer
from transformer.transformEncryptedData import TransformEncryptedData
from transformer.transformCleanData import TransformCleanData
from exporter.exportBinary import ExporterBinary
from exporter.exportJSONFromDataClass import ExportJSONFromDataClass

# ===== CONFIG =====
output_folder = "segments"
DOWNLOAD_RETRY = 5
# ==================

os.makedirs(output_folder, exist_ok=True)

# ==== args list =====
args = sys.argv
start_failed = "-f" in args
combine_video = "-c" in args
# ====================

type Header = dict[str, Any]


class Concurrency:
    def __init__(self, number: int):
        self.limit = asyncio.Semaphore(number)


class DownloadSegment:
    def __init__(
        self,
        concurrency: Concurrency,
        headers: Header,
        file_extension: str = "ts",
        retry: bool = False,
    ):
        self.concurrency = concurrency
        self.retry = retry
        self.headers = headers
        self.file_extension = file_extension

    # it return failed download list
    async def start(
        self, urls: list[Segment], transformer: Transformer
    ) -> list[Segment]:
        async with aiohttp.ClientSession() as session:
            tasks = [
                self._download_segment(session, data.url, data.index, transformer)
                for data in urls
            ]

            rr = await asyncio.gather(*tasks)

        return [item for item in rr if item is not None]

    async def _download_segment(
        self,
        session: aiohttp.ClientSession,
        url: str,
        index: int,
        transformer: Transformer,
    ) -> Segment | None:
        async with self.concurrency.limit:
            try:
                print(f"Downloading segment_{index}.{self.file_extension}")

                await asyncio.sleep(0.2)
                async with session.get(
                    url.strip(), headers=self.headers, timeout=aiohttp.ClientTimeout(10)
                ) as response:
                    response.raise_for_status()

                    file_path = os.path.join(
                        output_folder, f"segment_{index}.{self.file_extension}"
                    )

                    content = await response.read()

                    transformer.transform(content, exporter=ExporterBinary(file_path))

            except Exception as e:
                print(e)
                print(f"Failed to download {index} - {url}")

                return Segment(
                    url=url,
                    index=index,
                )


class Extract:
    def __init__(self, decoder: Decoder, download: DownloadSegment, exporter: Exporter):
        self.decoder = decoder
        self.download = download
        self.exporter = exporter

    async def run(self) -> None:
        segment = await self.decoder.decode()

        print(f"Found {len(segment.urls)} segment")

        # TODO: change based on m3u8 file
        transform: Transformer = TransformCleanData()

        if segment.is_encrypted:
            transform = TransformEncryptedData(segment.key)

        failed_download = await self.download.start(segment.urls, transform)

        self.exporter.export(
            Decode(
                urls=failed_download,
                is_encrypted=segment.is_encrypted,
                key=segment.key,
            )
        )

        print(f"Total Failed Download: {len(failed_download)}")

        create_segment_file(len(segment.urls), self.download.file_extension)

        print("Download Complete.")


# if url are base64 encoded
def decode_segment(encoded_part: str) -> str:
    """
    Extract and decode base64 string from /p/<base64>.ext
    """
    encoded_part = encoded_part.strip()

    # remove "/p/"
    encoded_part = encoded_part.split("/p/")[1]

    # remove file extension (.js, .vtt, etc.)
    encoded_part = encoded_part.split(".")[0]

    decoded = base64.b64decode(encoded_part).decode("utf-8")

    # only take the actual media URL (before |)
    real_url = decoded.split("|")[0]

    return real_url


def create_segment_file(total: int, extension: str = "ts") -> None:
    segment_file = os.path.join(output_folder, "files.txt")

    with open(segment_file, "w") as f:
        for i in range(total):
            f.write(f"file 'segment_{i}.{extension}'\n")


def run_combine_video() -> None:
    cmd = [
        "ffmpeg",
        "-f",
        "concat",
        "-safe",
        "0",
        "-i",
        "segments/files.txt",
        "-c",
        "copy",
        "output.mp4",
    ]
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, text=True)

    if process.stdout:
        for line in process.stdout:
            print(line.strip())

    return_code = process.wait()

    if return_code == 0:
        print("video segment combined successfully.")
    else:
        print("unable to combine video segment.")


def get_headers() -> dict[str, Any]:
    with open("headers.json", "r") as f:
        return json.load(f)


async def main() -> None:
    m3u8_file = "playlist.txt"  # playlist file name
    extension = "ts"

    if combine_video:
        run_combine_video()

        return

    headers = get_headers()

    decoder: Decoder = DecodeFullURL(
        filename=m3u8_file,
    )

    concurrency = Concurrency(10)

    if start_failed:
        decoder = DecodeFailList("fail.json")
        concurrency = Concurrency(1)

    service = Extract(
        decoder=decoder,
        download=DownloadSegment(
            concurrency=concurrency, headers=headers, file_extension=extension
        ),
        exporter=ExportJSONFromDataClass("fail.json"),
    )

    await service.run()


if __name__ == "__main__":
    asyncio.run(main())
