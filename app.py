import sys
import base64
import os
import requests
import asyncio
import aiohttp
import json
import subprocess
import io

# ===== CONFIG =====
m3u8_file = "playlist.txt"  # your uploaded file name
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

# ==== args list =====
args = sys.argv
check_for_invalid = "-x" in args
start_failed = "-f" in args
combine_video = "-c" in args
# ====================


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

    return real_url.strip()


async def download_segment(session: aiohttp.ClientSession, url: str, i: int):
    async with semaphore:
        try:
            print(f"Downloading segment_{i}.ts")

            await asyncio.sleep(0.2)
            async with session.get(url, headers=headers, timeout=10) as response:
                response.raise_for_status()

                file_path = os.path.join(output_folder, f"segment_{i}.ts")

                content = await response.read()

                if check_for_invalid:
                    clean_data(content, file_path)
                else:
                    with open(file_path, "wb") as f:
                        f.write(content)

        except Exception as e:
            print(e)
            failed_download.append({"url": url, "index": i})

            print(f"Failed to download {url}")


def clean_data(data, file_path):
    max_length = min(len(data), 2040)

    VIDEO_BYTE = 0x47

    for i in range(max_length):
        if data[i] == VIDEO_BYTE:
            # Verify it's not a fluke by checking the next packet (188 bytes later)
            # and a third packet (376 bytes later) for certainty.
            if (    
                i + 188 < len(data)
                and data[i + 188] == VIDEO_BYTE
                and i + 376 < len(data)
                and data[i + 376] == VIDEO_BYTE
            ):

                # Slice the bytes object to drop the fake header
                cleaned_data = data[i:]

                with open(file_path, "wb") as f:
                    f.write(cleaned_data)

                break


async def download(urls: list[str]):
    async with aiohttp.ClientSession() as session:
        tasks = [download_segment(session, url, i) for i, url in enumerate(urls)]

        await asyncio.gather(*tasks)


def download_sync(urls: list):
    for i in urls:
        count_retry = 0

        while count_retry < DOWNLOAD_RETRY:
            try:
                print(f"Downloading segment_{i['index']}.ts - {count_retry}")

                url = i["url"].strip()
                res = requests.get(url, headers=headers)
                res.raise_for_status()

                content = res.content

                file_path = os.path.join(output_folder, f"segment_{i['index']}.ts")

                if check_for_invalid:
                    clean_data(content, file_path)
                else:
                    with open(file_path, "wb") as f:
                        f.write(content)

                break

            except Exception as e:
                print(e)
                print(f"Failed to download segment_{i['index']}.ts - {i['url']}")

                count_retry += 1


def create_segment_file(total: int):
    segment_file = os.path.join(output_folder, "files.txt")

    with open(segment_file, "w") as f:
        for i in range(total):
            f.write(f"file 'segment_{i}.ts'\n")


async def main():
    segment_urls: list[str] = []

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

    # ========== this block of code is depend on m3u8_file =================
    with open(m3u8_file, "r", encoding="utf-8") as f:
        for line in f:
            # if line.startswith("/p/"):
            if line.startswith("https://"):
                try:
                    # url = decode_segment(line)
                    # base = (
                    #     "https://surrit.com/c5bf1a4a-ea0b-401f-9969-93056468b611/1080p/"
                    # )

                    # url = f"{base}{line}"
                    segment_urls.append(line)
                except Exception as e:
                    print(e)
                    print("Failed to decode:", line)
    # ===============================================================

    total_segment = len(segment_urls)
    print(f"Found {total_segment} segments")

    await download(segment_urls)

    print("Total failed download - ", len(failed_download))

    # store in fail.json file
    with open("fail.json", "w") as f:
        json.dump(failed_download, f)

    create_segment_file(total_segment)

    print("Download Complete.")


if __name__ == "__main__":
    asyncio.run(main())
