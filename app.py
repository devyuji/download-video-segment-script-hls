import sys
import base64
import os
import asyncio
import aiohttp
import json
import subprocess
from typing import Any, Callable
from pydantic import BaseModel
from type import Decode, Segment
from decoder import (
    DecodeFailList,
    DecodePartialURLWithInitial,
    Decoder,
    DecodeFullURL,
    DecodePartialURL,
    DecodeWithInitial,
)
from exporter.exportBinary import ExporterBinary
from exporter.exportJSONFromDataClass import ExportJSONFromDataClass
from transformer.transformer import Transformer
from transformer.transformEncryptedData import TransformEncryptedData
from transformer.transformCleanData import TransformCleanData
from transformer.tranformFytp import TransformFYTPOrMOOF
from transformer.transformNormal import TransformNormal

# ===== CONFIG =====
output_folder = "segments"
DOWNLOAD_RETRY = 5
# ==================

# ==== args list =====
args = sys.argv
start_failed = "-f" in args
combine_video = "-c" in args
# ====================

os.makedirs(output_folder, exist_ok=True)

type Header = dict[str, Any]


class Concurrency:
    def __init__(self, number: int):
        self.limit = asyncio.Semaphore(number)


class DownloadSegment:
    def __init__(
        self,
        urls: list[Segment],
        concurrency: Concurrency,
        headers: Header,
        transformer: Transformer,
        file_extension: str = "ts",
        retry: bool = False,
    ):
        self.urls = urls
        self.concurrency = concurrency
        self.retry = retry
        self.headers = headers
        self.transformer = transformer
        self.file_extension = file_extension
        self.retry = retry

    # it return failed download list
    async def start(self) -> list[Segment]:
        async with aiohttp.ClientSession() as session:
            tasks = [
                self._download_segment(session, data.url, data.index)
                for data in self.urls
            ]

            rr = await asyncio.gather(*tasks)

        return [item for item in rr if item is not None]

    async def _download_segment(
        self,
        session: aiohttp.ClientSession,
        url: str,
        index: int,
    ) -> Segment | None:
        async with self.concurrency.limit:
            try:
                print(f"Downloading segment_{index}.{self.file_extension}")

                await asyncio.sleep(0.2)
                async with session.get(
                    url.strip(), headers=self.headers, timeout=aiohttp.ClientTimeout(20)
                ) as response:
                    response.raise_for_status()

                    file_path = os.path.join(
                        output_folder, f"segment_{index}.{self.file_extension}"
                    )

                    content = await response.read()

                    self.transformer.transform(
                        content,
                        exporter=ExporterBinary(file_path),
                        index=index,
                    )

            except Exception as e:
                print(e)
                print(f"Failed to download {index} - {url}")

                return Segment(
                    url=url,
                    index=index,
                )


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


def get_headers() -> Header:
    with open("headers.json", "r") as f:
        return json.load(f)


async def main() -> None:
    transformer: dict[str, Callable[..., Transformer]] = {
        "clean_data": TransformCleanData,
        "encrypted": TransformEncryptedData,  # required segment.key
        "mp4": TransformFYTPOrMOOF,
        "normal": TransformNormal,
    }

    # -------------------- config --------------------

    m3u8_file = "playlist.txt"  # playlist file name
    extension = "mp4"  # change this depending on m3u8 file
    decoder: Decoder = DecodeFullURL(filename=m3u8_file)
    t = transformer["normal"]()

    # -------------------- config ---------------------

    if combine_video:
        run_combine_video()

        return

    headers = get_headers()

    concurrency = Concurrency(10)

    if start_failed:
        decoder = DecodeFailList("fail.json")
        concurrency = Concurrency(1)

    segment = await decoder.decode()
    segment_length = len(segment.urls)

    print(f"Total segment {segment_length} found")

    download = DownloadSegment(
        urls=segment.urls,
        concurrency=concurrency,
        headers=headers,
        transformer=t,
        file_extension=extension,
    )

    failed_download = await download.start()

    print(f"Total Failed Download: {len(failed_download)}")

    ExportJSONFromDataClass("fail.json").export(
        Decode(
            urls=failed_download,
            is_encrypted=segment.is_encrypted,
            key=segment.key,
        )
    )

    if not start_failed:
        create_segment_file(segment_length, extension)

    print("Download Complete.")


if __name__ == "__main__":
    asyncio.run(main())
