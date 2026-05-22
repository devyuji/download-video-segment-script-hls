import os
import asyncio
import aiohttp
from curl_cffi import AsyncSession, Response, requests
import json
import subprocess
from type import Decode, Segment, Header
import click
from urllib.parse import urlparse

# from combine_m4s_files import combine_binary_merge

from decoder.decoder import Decoder
from decoder.decode_playlist import DecodePlaylist
from decoder.decode_failed_list import DecodeFailList
# from decoder.decode_full_url import DecodeFullURL
# from decoder.decode_full_with_initial import DecodeWithInitial
# from decoder.decode_partial import DecodePartial
# from decoder.decode_partial_initial import DecodePartialURLWithInitial

from exporter.exportBinary import ExporterBinary
from exporter.exportJSONFromDataClass import ExportJSONFromDataClass

from transformer.transformer import Transformer
from transformer.transformCleanData import TransformCleanData
from transformer.transformEncryptedData import TransformEncryptedData
from transformer.tranformFytp import TransformFYTPOrMOOF
from transformer.transformNormal import TransformNormal


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
            impersonate="firefox147",
            timeout=10 * 60,
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
                    click.echo(
                        f"Downloading segment_{index}.{self.file_extension} - {count_retry}"
                    )

                    h = self.headers | create_header_based_on_url(url)

                    await asyncio.sleep(0.2)
                    response = await session.get(url=url, headers=h)
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

                    h = self.headers | create_header_based_on_url(url)

                    async with session.get(
                        url,
                        headers=h,
                        timeout=aiohttp.ClientTimeout(100),
                        allow_redirects=True,
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


def create_header_based_on_url(url: str) -> Header:
    parsed = urlparse(url)
    base_url = f"{parsed.netloc}"
    return {"Host": base_url}


async def main(
    decode: str,
    combine_ts: bool,
    base_url: str,
    find: str,
    concurrency: int,
) -> None:

    decoder: Decoder
    # -------------------- config --------------------

    output_folder = "output/segments-video"
    os.makedirs(output_folder, exist_ok=True)

    m3u8_file = "playlist.txt"  # playlist file name
    extension = "ts"  # change this depending on m3u8_file

    concurrency = Concurrency(concurrency)
    retry = False

    # -------------------- config ---------------------

    if combine_ts:
        run_combine_video(output_folder)

        return

    # if combine_video_mp4:
    #     combine_binary_merge(output_folder, extension)

    #     return

    headers = get_headers()

    fail_download = decode == "fail"

    # check for which decode to use
    match decode:
        case "fail":
            decoder = DecodeFailList("fail.json")
            retry = True

        case _:
            decoder = DecodePlaylist(filename=m3u8_file, base=base_url, find=find)

    segment = await decoder.decode()
    segment_length = len(segment.urls)

    # ------------------- change this based on m3u8 file --------------------------
    t = TransformCleanData()
    # -----------------------------------------------------------------------------

    click.echo(f"Total segment {segment_length} found")

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

    click.echo(f"Total Failed Download: {len(failed_download)}")

    ExportJSONFromDataClass(filename="fail.json").export(
        Decode(
            urls=failed_download,
            is_encrypted=segment.is_encrypted,
            key=segment.key,
        )
    )

    if not fail_download:
        create_segment_file(segment_length, output_folder, extension)

    click.echo("Download Complete.")


@click.group(invoke_without_command=True)
@click.option("--decode", "decode", type=str, default="")
@click.option("-d", "decode", type=str, default="")
@click.option("--base", "base_url", type=str, default="")
@click.option("--find", "find", type=str, default="")
@click.option("--combine-ts", "combine_ts", is_flag=True)
@click.option(
    "-x",
    "concurrency",
    type=int,
    default=10,
)
@click.pass_context
def cli(
    ctx,
    decode: str,
    combine_ts: bool,
    base_url: str,
    find: str,
    concurrency: int,
) -> None:
    if ctx.invoked_subcommand is None:
        asyncio.run(
            main(
                decode=decode,
                combine_ts=combine_ts,
                find=find,
                base_url=base_url,
                concurrency=concurrency,
            )
        )


@cli.command()
@click.argument("url", type=str, required=True)
def paste(url: str) -> None:
    asyncio.run(async_paste(url))


async def async_paste(url: str) -> None:
    try:
        uri = url.strip()
        headers = get_headers()

        click.echo("Fetching playlist.txt...")
        async with aiohttp.ClientSession() as session:
            async with session.get(uri, headers=headers) as response:
                response.raise_for_status()

                p = await response.text()

                with open("playlist.txt", "w") as f:
                    f.write(p)

                click.echo("Successfully saved to playlist.txt file")

    except Exception as err:
        print(err)
