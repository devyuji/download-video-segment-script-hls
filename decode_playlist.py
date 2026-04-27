import asyncio

from decoder.decode_full_url import DecodeFullURL


async def main() -> None:
    decode = DecodeFullURL(filename="playlist.txt")

    segments = await decode.decode()

    print(segments.urls[344])


if __name__ == "__main__":
    asyncio.run(main())
