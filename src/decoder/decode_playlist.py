from type import Segment, Decode
import re
import aiohttp


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
        urls: list[Segment] = []
        is_encrypted = False
        key = b""

        with open(self.filename, "r") as f:
            for line in f:
                u = ""

                # Check for initial url
                if line.startswith("#EXT-X-MAP"):
                    match = re.search(r'URI="([^"]+)"', line)

                    if match:
                        uri = match.group(1)

                        urls.append(Segment(url=uri, index=index))

                        index += 1
                    else:
                        raise ValueError("unable.to.get.url.")

                elif line.startswith(self.find):
                    if self.base.strip() == "":
                        u = line
                    else:
                        u = f"{self.base}{line}"

                    urls.append(Segment(url=u, index=index))

                    index += 1

                elif line.startswith("#EXT-X-KEY"):
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

        return Decode(urls=urls, is_encrypted=is_encrypted, key=key)
