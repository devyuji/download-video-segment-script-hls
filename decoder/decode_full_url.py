import re

import aiohttp

from type import Decode, Segment


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
                        raise ValueError("unable.to.get.key")

        return Decode(urls=segment_urls, is_encrypted=is_encrypted, key=key)
