import sys
import base64
import os
import requests
import asyncio
import aiohttp
import json
import subprocess

# ===== CONFIG =====
m3u8_file = "EXTM3U.txt"  # your uploaded file name
output_folder = "segments"
MAX_CONCURRENCY = 10
DOWNLOAD_RETRY = 10
# ==================

os.makedirs(output_folder, exist_ok=True)
failed_download: list = []
semaphore = asyncio.Semaphore(MAX_CONCURRENCY)
headers = {
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:148.0) Gecko/20100101 Firefox/148.0",
}


# if url are base64 encoded
def decode_segment(encoded_part):
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


async def download_segement(session: aiohttp.ClientSession, url: str, i: int):
    async with semaphore:
        try:
            print(f"Downloading segment_{i}.ts")

            asyncio.sleep(0.1)
            async with session.get(url, headers=headers, timeout=10) as response:
                response.raise_for_status()

                file_path = os.path.join(output_folder, f"segment_{i}.ts")

                content = await response.read()
                with open(file_path, "wb") as f:
                    f.write(content)

        except Exception as e:
            print(e)
            failed_download.append({"url": url, "index": i})

            print(f"Failed to download {url}")


async def download(urls: list[str]):
    async with aiohttp.ClientSession() as session:
        tasks = [download_segement(session, url, i) for i, url in enumerate(urls)]

        await asyncio.gather(*tasks)


def download_sync(urls: list):
    for i in urls:
        count_retry = 0

        while count_retry < DOWNLOAD_RETRY:
            try:
                print(f"Downloading segment_{i['index']}.ts - {count_retry}")

                res = requests.get(i["url"], headers=headers)
                res.raise_for_status()

                file_path = os.path.join(output_folder, f"segment_{i['index']}.ts")

                with open(file_path, "wb") as f:
                    f.write(res.content)

                break

            except Exception:
                print(f"Failed to download segment_{i['index']}.ts - {i['url']}")

                count_retry += 1


def create_files(total):
    segment_file = os.path.join(output_folder, "files.txt")

    with open(segment_file, "w") as f:
        for i in range(total):
            f.write(f"file 'segment_{i}.ts'\n")


async def main():
    segment_urls: list[str] = []

    args = sys.argv

    start_failed = "-f" in args

    combine_video = "-c" in args

    if start_failed:
        with open("fail.json", "r") as f:
            data = json.load(f)
            download_sync(data)

            print("Download Complete")

        return

    # running ffmpeg to combine segment
    if combine_video:
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

        result = subprocess.Popen(cmd, stdout=subprocess.PIPE, text=True)

        for i in result.stdout:
            print(i.strip())

        return

    with open(m3u8_file, "r", encoding="utf-8") as f:
        for line in f:
            if line.startswith("/p/"):
                try:
                    url = decode_segment(line)
                    segment_urls.append(url)
                except Exception as e:
                    print(e)
                    print("Failed to decode:", line)
            # if line.startswith("https:"):
            #     try:
            #         url = line.strip()
            #         segment_urls.append(url)
            #     except Exception:
            #         print("Failed  to decode")

    total_segment = len(segment_urls)
    print(f"Found {total_segment} segments")

    # await download(segment_urls)

    print("Total failed download - ", len(failed_download))

    # store in fail.json file
    with open("fail.json", "w") as f:
        json.dump(failed_download, f)

    create_files(total_segment)

    print("Download Complete.")


if __name__ == "__main__":
    asyncio.run(main())
