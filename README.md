# Script to download files from hsl encode videos.

## Understand the script

Everything is under src folder

app.py -> it is the main file.

Decoder -> it is what extract data from m3u8 file (playlist.txt).

Transformer -> it is what data need to be done like extract right data from it.

Exporter -> it is to save the transform file.

Change this depending on m3u8 file.

## REQUIREMENT

- [Python](https://python.org/)
- [FFMPEG](https://ffmpeg.org/)

## INSTALL USING UV

`git clone "https://github.com/devyuji/download-video-segment-script.git"`

Do this in a extracted folder

`uv sync`

`uv pip install -e .`

`uv run playwright install chromium`

## USAGE AND OPTIONS

_Create a playlist.txt in root folder and paste the video playlist in it._

_Create a headers.json root folder and paste the header required for video._

`uv run vd`

### OPTIONS

--decode, -d "How to parse data for download default is playlist.txt file

`uv run vd -d fail` - To download failed one

--base "If playlist.txt file has no url"

--find Custom find string to extract url from playlist.txt

`uv run vd --base "https://example.com/1080p/" --find "video"`

--combine-ts "To combine segment ts into single mp4 file"

`uv run vd --combine-ts`

--combine-mp4 "To combine segment mp4/m4s into single mp4 file"

`uv run vd --combine-mp4`

--use-browser "To replicate real browser"

`uv run vd --use-browser`

-x No. of concurrency download

`uv run vd -x 5`

_When using --use-browser it will only do 2 concurrency_

## MANUAL COMBINING TS FILES

`ffmpeg -f concat -safe 0 -i files.txt -c copy output.mp4`
