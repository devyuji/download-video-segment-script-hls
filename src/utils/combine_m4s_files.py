import os


# TODO: Find number of videos present in it
def _find_number_of_video(foldername: str) -> int:
    return 31


# --- The Ultimate fMP4 Binary Merger ---
def combine_binary_merge(output_folder: str, extension: str = "mp4") -> None:
    print("\n[+] Starting binary merge for fMP4...")

    total = _find_number_of_video(output_folder)

    name = f"output.{extension}"

    final_output = os.path.join(output_folder, name)

    # Open the final master file in "wb" (write binary) mode
    with open(final_output, "wb") as master_file:
        # 1. Write the Init Segment first (This gives the file its SPS/PPS headers)
        init_file = os.path.join(output_folder, f"segment_0.{extension}")

        if os.path.exists(init_file):
            with open(init_file, "rb") as f:
                master_file.write(f.read())
            print(f"    -> Added {init_file}")
        else:
            print(
                f"[-] ERROR: Could not find {init_file}! The video will not play without it."
            )

        # 2. Loop through all 100 segments and append their raw bytes
        for i in range(1, total + 1):
            segment_file = os.path.join(output_folder, f"segment_{i}.{extension}")

            if os.path.exists(segment_file):
                with open(segment_file, "rb") as f:
                    master_file.write(f.read())
                # Optional: Print every 10th segment so you know it's working
                if i % 10 == 0:
                    print(f"    -> Added up to {segment_file}...")
            else:
                print(f"[-] WARNING: Missing {segment_file}. Video might glitch here.")

    print(f"\n[+] Success! All files merged into {final_output}")


if __name__ == "__main__":
    combine_binary_merge("output/segments-video/")
