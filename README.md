# Script to download files from hsl encode videos.

## Understand the script

Everything is under src folder

app.py -> it is the main file.

Decoder -> it is what extract data from m3u8 file (playlist.txt).

Transformer -> it is what data need to be done like extract right data from it.

Exporter -> it is to save the transform file.

Change this depending on m3u8 file.

## Types of decoder

- "full" -> The playlist file in which all the url are present.

- "fwi" -> The playlist file in which initial url is present.

- "p" -> The playlist file in which partial url is present.

- "pi" -> The playlist file in which partial url is present with initial (#EXT-INITIAL-URI=).

- "fail" -> To download failed list

When running the script default decoder is "fu" you can change them by providing --decode <type>

`uv run vd --decode fwi`

## Running this script

`uv pip install -e .`

`uv run vd`

## Once the segment is loaded run this ffmpeg command (works for Transport Stream)

`uv run vd --combine-ts`

## OR

`ffmpeg -f concat -safe 0 -i files.txt -c copy output.mp4`

### For m4s/mp4 file run this command

`uv run app.py -cc`

** Change total_segment from file based on total number of files in segment folder. **
