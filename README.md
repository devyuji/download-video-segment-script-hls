# Script to download files from hsl encode videos.

## Understand the script

app.py -> it is the main file.

Decoder -> it is what extract data from m3u8 file (playlist.txt).

Transformer -> it is what data need to be done like extract right data from it.

Exporter -> it is to save the transform file.

Change this depending on m3u8 file.

## Running this script

` uv run app.py`

- if failed list is present then run
  `uv run app.py -f`

## Once the segment is loaded run this ffmpeg command (works for Transport Stream)

`uv run app.py -c`

## OR

`ffmpeg -f concat -safe 0 -i files.txt -c copy output.mp4`

### For m4s/mp4 file run this command

`uv run combine_m4s_files.py`

** Change total_segment from file based on total number of files in segment folder. **
