from exporter.exporter import Exporter
from Crypto.Cipher import AES


class TransformEncryptedData:
    def __init__(self, key: bytes, media_sequence_start: int):
        self.key = key
        self.media_sequence_start = media_sequence_start

    def transform(self, data: bytes, exporter: Exporter, index: int = 0) -> None:
        """
        Strips the plaintext HTML disguise and decrypts the AES-128 CBC payload.

        :param data: The raw binary downloaded from the .html URL
        """
        sequence_num = index

        iv = sequence_num.to_bytes(16, byteorder="big")

        max_search = min(len(data), 2048)
        decrypted_clean_data = None

        for i in range(max_search):
            remaining_length = len(data) - i
            if remaining_length % 16 == 0:
                test_ciphertext = data[i:]

                cipher = AES.new(self.key, AES.MODE_CBC, iv)

                test_decrypted_block = cipher.decrypt(test_ciphertext[:16])

                if test_decrypted_block[0] == 0x47:
                    print(f" -> Success! HTML disguise ends at byte {i}.")

                    cipher_full = AES.new(self.key, AES.MODE_CBC, iv)
                    decrypted_clean_data = cipher_full.decrypt(test_ciphertext)
                    break

        if decrypted_clean_data is None:
            print(
                "[-] Decryption failed. Could not find a valid 0x47 sync byte inside the ciphertext."
            )
            raise ValueError("decryption.failed")

        # 5. Save the perfectly clean, decrypted .ts file
        exporter.export(decrypted_clean_data)

    # def transform(self, data: bytes, exporter: Exporter, index: int = 0) -> None:
    #     """
    #     Cracks AES-128 CBC encryption that uses misaligned injected bytes.
    #     """
    #     sequence_num = index + self.media_sequence_start
    #     iv = sequence_num.to_bytes(16, byteorder="big")

    #     max_search = min(len(data), 2048)
    #     decrypted_clean_data = None
    #     detected_format = None
    #     true_start_index = -1

    #     print(f"[*] Commencing sliding window AES crack on segment {index}...")

    #     # We test EVERY SINGLE byte index up to max_search
    #     for i in range(max_search):

    #         # Grab exactly 16 bytes starting at index 'i'
    #         # We don't care if the total remaining length is divisible by 16 yet
    #         if i + 16 > len(data):
    #             break

    #         test_ciphertext = data[i:i+16]
    #         cipher = AES.new(self.key, AES.MODE_CBC, iv)
    #         test_decrypted_block = cipher.decrypt(test_ciphertext)

    #         # Check 1: Transport Stream
    #         if test_decrypted_block[0] == 0x47:
    #             # Make sure we have enough data left to check the next packet
    #             if len(test_ciphertext) >= 188 + 16:
    #                 verify_block = cipher.decrypt(test_ciphertext[188:188+16])
    #                 if verify_block[0] == 0x47:
    #                     detected_format = ".ts"
    #                     true_start_index = i
    #                     print(f"    -> CRACKED! True TS detected at byte {i}.")
    #                     break

    #         # Check 2: Fragmented MP4
    #         box_signature = test_decrypted_block[4:8]
    #         if box_signature == b"moof" or box_signature == b"ftyp":
    #             detected_format = ".mp4"
    #             true_start_index = i
    #             box_type = box_signature.decode('ascii')
    #             print(f"    -> CRACKED! Disguise ends at byte {i}. Format: fMP4 ({box_type})")
    #             break

    #     if true_start_index == -1:
    #         print("[-] Decryption failed. Sliding window found no valid headers.")
    #         raise ValueError("decryption.failed")

    #     # --- The Final Alignment & Decryption ---

    #     # Now that we know exactly where the true encrypted data starts,
    #     # we must ensure we only feed perfect 16-byte blocks to the full decryptor.
    #     # Any leftover bytes at the very end of the file are fake padding!

    #     valid_ciphertext = data[true_start_index:]
    #     perfect_length = len(valid_ciphertext) - (len(valid_ciphertext) % 16)
    #     aligned_ciphertext = valid_ciphertext[:perfect_length]

    #     cipher_full = AES.new(self.key, AES.MODE_CBC, iv)
    #     decrypted_clean_data = cipher_full.decrypt(aligned_ciphertext)

    #     # Save the file
    #     exporter.export(decrypted_clean_data)
