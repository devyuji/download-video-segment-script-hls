import base64
import os

from Crypto.Cipher import AES

key_b64 = ""


def try_decrypt(iv_int):
    iv_bytes = iv_int.to_bytes(16, byteorder="big")

    with open("a.ts", "r", encoding="utf-8") as f:
        d = f.read().strip()
        encrypted_data = base64.b64decode(d)
        # encrypted_data = f.read()

    max_search = min(len(encrypted_data), 2048)
    decrypted_clean_data = None

    for i in range(max_search):
        remaining_length = len(encrypted_data) - i
        if remaining_length % 16 == 0:
            test_ciphertext = encrypted_data[i:]

            cipher = AES.new(key_bytes, AES.MODE_CBC, iv_bytes)

            test_decrypted_block = cipher.decrypt(test_ciphertext[:16])

            if test_decrypted_block[0] == 0x47:
                print(f" -> Success! HTML disguise ends at byte {i}.")

                cipher_full = AES.new(key_bytes, AES.MODE_CBC, iv_bytes)
                decrypted_clean_data = cipher_full.decrypt(test_ciphertext)
                break

        if decrypted_clean_data is None:
            print(
                "[-] Decryption failed. Could not find a valid 0x47 sync byte inside the ciphertext."
            )

            raise ValueError("decryption.failed")

    return decrypted_clean_data


index = 340

data = try_decrypt(index)
# if data and data[0] != 0x47:
#     data = try_decrypt(index + 1)
# if data and data[0] != 0x47:
#     data = try_decrypt(index - 1)
# if data and data[0] != 0x47:
#     data = try_decrypt(1)

# Just save whatever we got with IV 238 to analyze
if data:
    file_path = os.path.join("output", "New Folder", f"segment_{index}.ts")
    with open(file_path, "wb") as f:
        f.write(data)
