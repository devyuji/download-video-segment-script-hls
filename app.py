import sys
import base64
import os
import asyncio
import aiohttp
from curl_cffi import AsyncSession, Response, requests
import json
import subprocess
from typing import Any
from combine_m4s_files import combine_binary_merge
from type import Decode, Segment

from decoder.decoder import Decoder
from decoder.decode_failed_list import DecodeFailList
from decoder.decode_full_url import DecodeFullURL
from decoder.decode_full_with_initial import DecodeWithInitial
from decoder.decode_partial import DecodePartial
from decoder.decode_partial_initial import DecodePartialURLWithInitial


from exporter.exportBinary import ExporterBinary
from exporter.exportJSONFromDataClass import ExportJSONFromDataClass
from transformer.transformer import Transformer
from transformer.transformEncryptedData import TransformEncryptedData
from transformer.transformCleanData import TransformCleanData
from transformer.tranformFytp import TransformFYTPOrMOOF
from transformer.transformNormal import TransformNormal

# =========== args list =============
args = sys.argv
start_failed = "-f" in args
combine_video = "-c" in args
combine_video_mp4 = "-cc" in args
# ===================================


type Header = dict[str, Any]


class Concurrency:
    def __init__(self, number: int = 10):
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
        output_folder: str = "segments",
    ):
        self.urls = urls
        self.concurrency = concurrency
        self.retry = retry
        self.headers = headers
        self.transformer = transformer
        self.file_extension = file_extension
        self.retry = retry
        self.output_folder = output_folder


class DownloadWithSpoof(DownloadSegment):
    async def start(self) -> list[Segment]:
        async with requests.AsyncSession(
            impersonate="firefox147", timeout=100
        ) as session:
            tasks = [
                self._download_segment(session, data.url, data.index)
                for data in self.urls
            ]

            rr = await asyncio.gather(*tasks)

        return [item for item in rr if item is not None]

    async def _download_segment(
        self,
        session: AsyncSession[Response],
        url: str,
        index: int,
    ) -> Segment | None:

        count_retry = 1
        async with self.concurrency.limit:
            while True:
                try:
                    print(
                        f"Downloading segment_{index}.{self.file_extension} - {count_retry}"
                    )

                    await asyncio.sleep(0.2)
                    response = await session.get(url.strip())
                    response.raise_for_status()

                    file_path = os.path.join(
                        self.output_folder, f"segment_{index}.{self.file_extension}"
                    )

                    content = response.content

                    self.transformer.transform(
                        content,
                        exporter=ExporterBinary(file_path),
                        index=index,
                    )
                    break

                except Exception as e:
                    print(e)
                    print(f"Failed to download {index} - {url}")

                    if not (self.retry):
                        return Segment(
                            url=url,
                            index=index,
                        )

                    if count_retry >= 10:
                        return Segment(
                            url=url,
                            index=index,
                        )

                    count_retry += 1


class DownloadNormal(DownloadSegment):
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
        count_retry = 1

        async with self.concurrency.limit:
            while True:
                try:
                    print(
                        f"Downloading segment_{index}.{self.file_extension} - {count_retry}"
                    )

                    await asyncio.sleep(0.2)
                    async with session.get(
                        url.strip(),
                        headers=self.headers,
                        timeout=aiohttp.ClientTimeout(100),
                    ) as response:
                        response.raise_for_status()

                        file_path = os.path.join(
                            self.output_folder, f"segment_{index}.{self.file_extension}"
                        )

                        content = await response.read()

                        self.transformer.transform(
                            content,
                            exporter=ExporterBinary(file_path),
                            index=index,
                        )
                    break

                except Exception as e:
                    print(e)
                    print(f"Failed to download {index} - {url}")

                    if not (self.retry):
                        return Segment(
                            url=url,
                            index=index,
                        )

                    if count_retry >= 10:
                        return Segment(
                            url=url,
                            index=index,
                        )

                    count_retry += 1


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


def create_segment_file(
    total: int,
    output_folder: str,
    extension: str = "ts",
) -> None:
    segment_file = os.path.join(output_folder, "files.txt")

    with open(segment_file, "w") as f:
        for i in range(total):
            f.write(f"file 'segment_{i}.{extension}'\n")


def run_combine_video(output_folder: str) -> None:
    cmd = [
        "ffmpeg",
        "-f",
        "concat",
        "-safe",
        "0",
        "-i",
        f"{output_folder}/files.txt",
        "-c",
        "copy",
        "output.mp4",
    ]
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, text=True)

    if process.stdout:
        for line in process.stdout:
            print(line.strip())

    process.wait()


def get_headers() -> Header:
    with open("headers.json", "r") as f:
        return json.load(f)


async def main() -> None:
    # transformer: dict[str, type[Transformer]] = {
    #     "clean_data": TransformCleanData,
    #     "encrypted": TransformEncryptedData,  # required segment.key
    #     "mp4": TransformFYTPOrMOOF,
    #     "normal": TransformNormal,
    # }

    # -------------------- config --------------------

    output_folder = "output/segments-video"
    os.makedirs(output_folder, exist_ok=True)

    m3u8_file = "playlist.txt"  # playlist file name
    extension = "ts"  # change this depending on m3u8_file

    decoder: Decoder = DecodeFullURL(filename=m3u8_file)
    concurrency = Concurrency(10)
    retry = False

    # -------------------- config ---------------------

    if combine_video:
        run_combine_video(output_folder)

        return

    if combine_video_mp4:
        combine_binary_merge(100, output_folder, extension)

        return

    headers = get_headers()

    if start_failed:
        decoder = DecodeFailList("fail.json")
        concurrency = Concurrency(2)
        retry = True

    segment = await decoder.decode()
    segment_length = len(segment.urls)

    # ------------------- change this based on m3u8 file --------------------------
    t = TransformCleanData()
    # -----------------------------------------------------------------------------

    print(f"Total segment {segment_length} found")

    download = DownloadWithSpoof(
        urls=segment.urls,
        concurrency=concurrency,
        headers=headers,
        transformer=t,
        file_extension=extension,
        output_folder=output_folder,
        retry=retry,
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
        create_segment_file(segment_length, output_folder, extension)

    print("Download Complete.")


if __name__ == "__main__":
    asyncio.run(main())
