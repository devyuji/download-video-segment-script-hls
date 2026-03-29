import re
import aiohttp
from typing import Protocol
from type import Decode, Segment


class Decoder(Protocol):
    async def decode(self) -> Decode: ...


class DecodeFullURL:
    def __init__(self, filename: str) -> None:
        self.filename = filename

    async def decode(self) -> Decode:
        segment_urls: list[Segment] = []
        is_encrypted = False
        key = b""

        with open(self.filename, "r", encoding="utf-8") as f:
            index = 0
            for line in f:
                if line.startswith("https"):
                    try:
                        segment_urls.append(Segment(url=line, index=index))

                        index += 1
                    except Exception as e:
                        print(e)
                        print("Failed to decode:", line)

                if line.startswith("#EXT-X-KEY"):
                    is_encrypted = True

                    match = re.search(r'URI="([^"]+)"', line)

                    if match:
                        key_uri = match.group(1)

                        async with aiohttp.ClientSession() as session:
                            async with session.get(key_uri) as response:
                                content = await response.read()
                                key = content

                    else:
                        raise ValueError("unable.to.get.uri")

        return Decode(urls=segment_urls, is_encrypted=is_encrypted, key=key)


class DecodePartialURL:
    def __init__(self, filename: str, base: str, find: str) -> None:
        self.filename = filename
        self.base = base
        self.find = find

    async def decode(self) -> Decode:
        segment_urls: list[Segment] = []
        is_encrypted = False
        key = b""

        with open(self.filename, "r", encoding="utf-8") as f:
            index = 0
            for line in f:
                if line.startswith(self.find):
                    try:
                        url = f"{self.base}{line}"
                        segment_urls.append(Segment(url=url, index=index))

                        index += 1
                    except Exception as e:
                        print(e)
                        print("Failed to decode:", line)

                if line.startswith("#EXT-X-KEY"):
                    is_encrypted = True

                    match = re.search(r'URI="([^"]+)"', line)

                    if match:
                        key_uri = match.group(1)

                        async with aiohttp.ClientSession() as session:
                            async with session.get(key_uri) as response:
                                content = await response.read()
                                key = content

                    else:
                        raise ValueError("unable.to.get.uri")

        return Decode(urls=segment_urls, is_encrypted=is_encrypted, key=key)


class DecodePartialURLWithInitial:
    def __init__(self, filename: str, base: str, find: str) -> None:
        self.filename = filename
        self.base = base
        self.find = find

    async def decode(self) -> Decode:
        segment_urls: list[Segment] = []
        is_encrypted = False
        key = b""

        with open(self.filename, "r", encoding="utf-8") as f:
            index = 0
            for line in f:
                if line.startswith("#EXT-X-MAP"):
                    match = re.search(r'URI="([^"]+)"', line)

                    if match:
                        uri = match.group(1)

                        url = f"{self.base}{uri}"
                        segment_urls.append(Segment(url=url, index=index))

                        index += 1

                if line.startswith(self.find):
                    try:
                        url = f"{self.base}{line}"
                        segment_urls.append(Segment(url=url, index=index))

                        index += 1
                    except Exception as e:
                        print(e)
                        print("Failed to decode:", line)

                if line.startswith("#EXT-X-KEY"):
                    is_encrypted = True

                    match = re.search(r'URI="([^"]+)"', line)

                    if match:
                        key_uri = match.group(1)

                        async with aiohttp.ClientSession() as session:
                            async with session.get(key_uri) as response:
                                content = await response.read()
                                key = content

                    else:
                        raise ValueError("unable.to.get.uri")

        return Decode(urls=segment_urls, is_encrypted=is_encrypted, key=key)

class DecodeWithInitial:
    def __init__(self, filename: str, find: str) -> None:
        self.filename = filename
        self.find = find

    async def decode(self) -> Decode:
        segment_urls: list[Segment] = []
        is_encrypted = False
        key = b""

        with open(self.filename, "r", encoding="utf-8") as f:
            index = 0
            for line in f:
                if line.startswith("#EXT-X-MAP"):
                    match = re.search(r'URI="([^"]+)"', line)

                    if match:
                        uri = match.group(1)

                        segment_urls.append(Segment(url=uri, index=index))

                        index += 1

                if line.startswith(self.find):
                    try:
                        segment_urls.append(Segment(url=line, index=index))

                        index += 1
                    except Exception as e:
                        print(e)
                        print("Failed to decode:", line)

                if line.startswith("#EXT-X-KEY"):
                    is_encrypted = True

                    match = re.search(r'URI="([^"]+)"', line)

                    if match:
                        key_uri = match.group(1)

                        async with aiohttp.ClientSession() as session:
                            async with session.get(key_uri) as response:
                                content = await response.read()
                                key = content

                    else:
                        raise ValueError("unable.to.get.uri")

        return Decode(urls=segment_urls, is_encrypted=is_encrypted, key=key)

class DecodeFailList:
    def __init__(self, filename) -> None:
        self.filename = filename

    async def decode(self) -> Decode:
        with open(self.filename, "r") as f:
            data = f.read()

            d = Decode.model_validate_json(data)

            return d
