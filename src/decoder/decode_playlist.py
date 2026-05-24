from utils.get_headers import get_headers
from type import Segment, Decode
import re
import aiohttp
import click


class DecodePlaylist:
    def __init__(self, filename: str, base: str, find: str = "https") -> None:
        self.filename = filename
        self.base = base

        if find == "":
            self.find = "https"
        else:
            self.find = find

    async def decode(self) -> Decode:
        index = 0
        # urls: list[Segment] = []
        # is_encrypted = False
        # key = b""
        d = Decode(urls=[])

        with open(self.filename, "r") as f:
            for line in f:
                u = ""

                # Check for initial url
                if line.startswith("#EXT-X-MAP"):
                    match = re.search(r'URI="([^"]+)"', line)

                    if match:
                        uri = match.group(1)

                        d.urls.append(Segment(url=uri, index=index))

                        index += 1
                    else:
                        raise ValueError("unable.to.get.url.")

                # Finding the urls
                elif line.startswith(self.find):
                    if self.base.strip() == "":
                        u = line
                    else:
                        u = f"{self.base}{line}"

                    d.urls.append(Segment(url=u, index=index))

                    index += 1

                # Getting encrypted key
                elif line.startswith("#EXT-X-KEY"):
                    d.is_encrypted = True

                    match = re.search(r'URI="([^"]+)"', line)

                    if match:
                        key_uri = match.group(1)

                        headers = get_headers()

                        click.echo("Getting encrypted key..")

                        async with aiohttp.ClientSession() as session:
                            async with session.get(
                                key_uri,
                                headers=headers,
                            ) as response:
                                response.raise_for_status()

                                content = await response.read()
                                d.key = content
                                click.echo("Found Encrypted Key")

                    else:
                        raise ValueError("unable.to.get.key")

                # Getting the media sequence
                elif line.startswith("#EXT-X-MEDIA-SEQUENCE"):
                    n = line.split(":")
                    d.media_sequence = int(n[-1])

        return d
