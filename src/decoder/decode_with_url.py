import aiohttp

from decoder.decode_full_url import DecodeFullURL
from type import Decode
import click


class DecodeWithURL:
    def __init__(self, url: str, headers: dict[str, str], filename: str) -> None:
        self.url = url
        self.headers = headers
        self.filename = filename

    async def decode(self) -> Decode:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(self.url, headers=self.headers) as response:
                    content = await response.text()

                    with open(self.filename, "w") as f:
                        f.write(content)

                    return await DecodeFullURL(self.filename).decode()

        except Exception as err:
            click.echo(f"unable to get the file - {err}")
            return Decode(urls=[], is_encrypted=False, key=b"")
