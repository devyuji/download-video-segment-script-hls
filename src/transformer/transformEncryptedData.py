from exporter.exporter import Exporter
from Crypto.Cipher import AES


class TransformEncryptedData:
    def __init__(
        self, key: bytes, media_sequence_start: int = 0, iv: bytes | None = None
    ):
        self.key = key
        self.media_sequence_start = media_sequence_start  # X-MEDIA-SEQUENCE
        self.iv = iv

    def transform(
        self,
        data: bytes,
        exporter: Exporter,
        index: int = 0,
    ) -> None:
        """
        Strips the plaintext HTML disguise and decrypts the AES-128 CBC payload.

        :param data: The raw binary downloaded from the .html URL
        """

        iv = None

        if self.iv:
            iv = self.iv
        else:
            sequence_num = index + self.media_sequence_start
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
