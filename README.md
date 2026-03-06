# Script to download files from hsl encode videos.

## Running this script

` uv run app.py`

- if failed list is present then run
  `uv run app.py -f`

## Once the segment is loaded run this ffmpeg command

`uv run app.py -c`

## OR

`ffmpeg -f concat -safe 0 -i files.txt -c copy output.mp4`