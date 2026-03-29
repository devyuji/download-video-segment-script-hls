from exporter.exporter import Exporter


class TransformFYTPOrMOOF:
    def transform(self, data: bytes, exporter: Exporter):
        try:
            # 1. Search for 'moof' (Media Segment) or 'ftyp' (Init Segment)
            moof_index = data.find(b"moof")
            ftyp_index = data.find(b"ftyp")

            start_index = -1
            box_type = ""

            # Determine which one we found and calculate the true start (4 bytes before the text)
            if moof_index >= 4:
                start_index = moof_index - 4
                box_type = "moof"
            elif ftyp_index >= 4:
                start_index = ftyp_index - 4
                box_type = "ftyp"

            # 2. Crop and Save!
            if start_index != -1:
                print(
                    f"[+] Fake header bypassed. '{box_type}' box found. Segment starts at byte {start_index}."
                )

                cleaned_data = data[start_index:]

                exporter.export(cleaned_data)

            else:
                print(
                    "[-] No 'moof' or 'ftyp' found! The file might be encrypted, empty, or not disguised."
                )
                # Fallback: Just save the raw data in case it wasn't disguised at all

        except Exception as err:
            print(err)
            raise ValueError("unablet.to.decode.FYPT/MOOF.segment")
