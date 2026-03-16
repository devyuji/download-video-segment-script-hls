import sys
import re
import base64
import os
import asyncio
import aiohttp
import json
import subprocess
from Crypto.Cipher import AES
from dataclasses import dataclass, asdict

# ===== CONFIG =====
m3u8_file = "playlist.txt"  # your uploaded file name
output_folder = "segments"
MAX_CONCURRENCY = 10
DOWNLOAD_RETRY = 5
# ==================


@dataclass
class FailData:
    index: int
    url: str
    is_encrypted: bool
    key: str = ""

    def __post_init__(self):
        self.url = self.url.strip()


os.makedirs(output_folder, exist_ok=True)
failed_download: list[FailData] = []
semaphore = asyncio.Semaphore(MAX_CONCURRENCY)
headers = {
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:148.0) Gecko/20100101 Firefox/148.0",
}
is_encrypted = False
key: bytes = b""

# ==== args list =====
args = sys.argv
start_failed = "-f" in args
combine_video = "-c" in args
# ====================


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


async def download_segment(
    session: aiohttp.ClientSession, url: str, index: int
) -> None:
    async with semaphore:
        try:
            print(f"Downloading segment_{index}.ts")

            await asyncio.sleep(0.2)
            async with session.get(
                url.strip(), headers=headers, timeout=10
            ) as response:
                response.raise_for_status()

                file_path = os.path.join(output_folder, f"segment_{index}.ts")

                content = await response.read()

                if is_encrypted:
                    clean_and_decrypt_segment(content, key, index, file_path)

                    return

                clean_data(content, file_path)

        except Exception as e:
            print(e)
            failed_download.append(
                FailData(
                    url=url,
                    index=index,
                    is_encrypted=is_encrypted,
                    key=key.decode("utf-8"),
                )
            )

            print(f"Failed to download {url}")


def clean_and_decrypt_segment(
    raw_data: bytes, key_bytes: bytes, sequence_num: int, output_filename: str
) -> None:
    """
    Strips the plaintext HTML disguise and decrypts the AES-128 CBC payload.

    :param raw_data: The raw binary downloaded from the .html URL
    """
    print(f"[+] Attempting to crack and clean segment {sequence_num}...")

    iv = sequence_num.to_bytes(16, byteorder="big")

    max_search = min(len(raw_data), 2048)
    decrypted_clean_data = None

    for i in range(max_search):
        remaining_length = len(raw_data) - i
        if remaining_length % 16 == 0:
            test_ciphertext = raw_data[i:]

            cipher = AES.new(key_bytes, AES.MODE_CBC, iv)

            test_decrypted_block = cipher.decrypt(test_ciphertext[:16])

            if test_decrypted_block[0] == 0x47:
                print(f"    -> Success! HTML disguise ends at byte {i}.")

                cipher_full = AES.new(key_bytes, AES.MODE_CBC, iv)
                decrypted_clean_data = cipher_full.decrypt(test_ciphertext)
                break

    if decrypted_clean_data is None:
        print(
            "[-] Decryption failed. Could not find a valid 0x47 sync byte inside the ciphertext."
        )
        return

    # 5. Save the perfectly clean, decrypted .ts file
    with open(output_filename, "wb") as f:
        f.write(decrypted_clean_data)


def clean_data(data: bytes, file_path: str) -> None:
    max_length = min(len(data), 2040)

    VIDEO_BYTE = 0x47

    for i in range(max_length):
        if data[i] == VIDEO_BYTE:
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


async def download(urls: list[str]) -> None:
    async with aiohttp.ClientSession() as session:
        tasks = [
            download_segment(session, url, index) for index, url in enumerate(urls)
        ]

        await asyncio.gather(*tasks)


async def download_sync(urls: list[FailData]) -> None:
    async with aiohttp.ClientSession() as session:
        for i in urls:
            count_retry = 0

            while count_retry < DOWNLOAD_RETRY:
                try:
                    print(f"Downloading segment_{i.index}.ts - {count_retry}")

                    async with session.get(i.url, headers=headers) as response:
                        response.raise_for_status()

                        content = await response.read()

                        file_path = os.path.join(output_folder, f"segment_{i.index}.ts")

                        if i.is_encrypted:
                            clean_and_decrypt_segment(
                                content, i.key.encode("utf-8"), i.index, file_path
                            )
                        else:
                            clean_data(content, file_path)

                        break

                except Exception as e:
                    print(e)
                    print(f"Failed to download segment_{i.index}.ts - {i.url}")

                    count_retry += 1


def create_segment_file(total: int) -> None:
    segment_file = os.path.join(output_folder, "files.txt")

    with open(segment_file, "w") as f:
        for i in range(total):
            f.write(f"file 'segment_{i}.ts'\n")


def run_combine_video() -> None:
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


async def main() -> None:
    segment_urls: list[str] = []

    if start_failed:
        with open("fail.json", "r") as f:
            global failed_download

            data = json.load(f)
            urls = [FailData(**i) for i in data]
            failed_download = urls
            await download_sync(urls)

            print("Download Complete")

        return

    # running ffmpeg to combine segment
    if combine_video:
        run_combine_video()
        return

    # ========== this block of code is depend on m3u8_file =================
    with open(m3u8_file, "r", encoding="utf-8") as f:
        for line in f:
            # if line.startswith("/p/"):
            if line.startswith("https://"):
                try:
                    # url = decode_segment(line)
                    # base = "https://surrit.com/fdd9638e-28a0-4d75-9093-e80f0bdbc97f/1920x1080/"

                    # url = f"{base}{line}"
                    segment_urls.append(line)
                except Exception as e:
                    print(e)
                    print("Failed to decode:", line)

            if line.startswith("#EXT-X-KEY"):
                global is_encrypted
                global key

                is_encrypted = True

                match = re.search(r'URI="([^"]+)"', line)

                if match:
                    key_uri = match.group(1)

                else:
                    raise ValueError("unable.to.get.uri")

                async with aiohttp.ClientSession() as session:
                    async with session.get(key_uri) as response:
                        content = await response.read()
                        key = content

    # ===============================================================

    total_segment = len(segment_urls)
    print(f"Found {total_segment} segments")

    await download(segment_urls)

    print("Total failed download - ", len(failed_download))

    # store in fail.json file
    with open("fail.json", "w") as f:
        data_to_save = [asdict(data) for data in failed_download]
        json.dump(data_to_save, f)

    create_segment_file(total_segment)

    print("Download Complete.")


if __name__ == "__main__":
    asyncio.run(main())
