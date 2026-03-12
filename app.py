import sys
import base64
import os
import requests
import asyncio
import aiohttp
import json
import subprocess
import io
from Crypto.Cipher import AES

# ===== CONFIG =====
m3u8_file = "playlist.txt"  # your uploaded file name
key_file = "key.txt"
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
is_encrypted = False
key = None

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

    return real_url


async def download_segment(session: aiohttp.ClientSession, url: str, i: int):
    async with semaphore:
        try:
            print(f"Downloading segment_{i}.ts")

            await asyncio.sleep(0.2)
            async with session.get(url.strip(), headers=headers, timeout=10) as response:
                response.raise_for_status()

                file_path = os.path.join(output_folder, f"segment_{i}.ts")

                content = await response.read()

                if is_encrypted:
                    clean_and_decrypt_segment(content, key, i, file_path)

                else:
                    if check_for_invalid:
                        clean_data(content, file_path)
                    else:
                        with open(file_path, "wb") as f:
                            f.write(content)

        except Exception as e:
            print(e)
            failed_download.append({"url": url, "index": i, "is_encrypted": is_encrypted})

            print(f"Failed to download {url}")

def clean_and_decrypt_segment(raw_data, key_bytes, sequence_num, output_filename):
    """
    Strips the plaintext HTML disguise and decrypts the AES-128 CBC payload.
    
    :param raw_data: The raw binary downloaded from the .html URL
    """
    print(f"[+] Attempting to crack and clean segment {sequence_num}...")

    # 1. In HLS, the IV is the sequence number padded to 16 bytes (128 bits)
    iv = sequence_num.to_bytes(16, byteorder='big')

    # We will search the first 2048 bytes for the end of the HTML disguise
    max_search = min(len(raw_data), 2048)
    decrypted_clean_data = None

    for i in range(max_search):
        # 2. Check if the remaining bytes form perfect 16-byte AES blocks
        remaining_length = len(raw_data) - i
        if remaining_length % 16 == 0:
            
            # 3. We found a valid AES boundary! Let's test it.
            test_ciphertext = raw_data[i:]
            
            # Create a fresh AES cipher for this test
            cipher = AES.new(key_bytes, AES.MODE_CBC, iv)
            
            # Decrypt just the first 16 bytes to save CPU power
            test_decrypted_block = cipher.decrypt(test_ciphertext[:16])
            
            # 4. Did the decryption reveal the hidden Transport Stream?
            if test_decrypted_block[0] == 0x47:
                print(f"    -> Success! HTML disguise ends at byte {i}.")
                
                # Now decrypt the entire rest of the file
                cipher_full = AES.new(key_bytes, AES.MODE_CBC, iv)
                decrypted_clean_data = cipher_full.decrypt(test_ciphertext)
                break

    if decrypted_clean_data is None:
        print("[-] Decryption failed. Could not find a valid 0x47 sync byte inside the ciphertext.")
        return

    # 5. Save the perfectly clean, decrypted .ts file
    with open(output_filename, "wb") as f:
        f.write(decrypted_clean_data)
        
    print(f"[+] Decrypted video saved to {output_filename}")
    return


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

                if i['is_encrypted']:
                    with open(key_file, "r") as f:
                        global key
                        key = f.read().encode("utf-8")
                    
                    clean_and_decrypt_segment(content, key, i['index'], file_path)
                else:
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
                    #     "https://surrit.com/64b24b84-cb0c-4d1e-a4d7-ebe463eaad6f/1080p/"
                    # )

                    # url = f"{base}{line}"
                    segment_urls.append(line)
                except Exception as e:
                    print(e)
                    print("Failed to decode:", line)

            if line.startswith("#EXT-X-KEY"):
                global is_encrypted
                global key

                is_encrypted = True

                with open(key_file, "r") as f:
                    key = f.read().encode("utf-8")
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
