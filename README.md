# DeepMark Client API examples

Embed and detect watermarks in audio, video and images with the [DeepMark Client API](https://www.deepmark.me/docs/api/key-guide).

| File | What it does |
|---|---|
| `deepmark_quickstart.py` | Discover models, embed a random watermark, then detect it. |
| `deepmark_quickstart.sh` | Embed and detect with curl using a model and watermark you choose. |
| `callback_receiver.py` | Receive job callbacks and download results. |
| `samples/speech.wav` | 11 seconds of public-domain LibriVox speech (16 kHz mono). |

## Before you start

Sign in to the [DeepMark web app](https://app.deepmark.me/key), open **API Key** and click **Generate API Key**. Copy the key; it is shown once. For an account, [contact us](https://www.deepmark.me/contact).

```bash
export DEEPMARK_API_KEY="paste-your-api-key-here"
```

## Python

Python 3.10 or newer, as required by `requests` in `requirements.txt`. On Debian and Ubuntu, install the venv module first (`sudo apt install python3-venv`).

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python deepmark_quickstart.py samples/speech.wav
```

Without a model `_id`, the script lists available models for the file type. Run it again with an `_id` from that list:

```bash
python deepmark_quickstart.py samples/speech.wav 6ab529a18d7eecb6f6d43f87
```

Example output:

```text
model: vigil-multibit-32b-a91 v1.0
embed job: 3039d026-1039-4e83-b3ba-e068f00d5206
  waiting: HTTP 400 {"detail":"Result not available yet"}
saved watermarked.wav
detect job: 3101f9b9-a97b-494d-ad20-71f081e84541
  waiting: HTTP 400 {"detail":"Result not available yet"}
watermark found: True
embedded:  01111101111101110011111001001000
extracted: 01111101111101110011111001001000
```

For images, pass a `.png` or `.jpg` file and an image model. Polling uses a 30-minute limit per job. Python reads the file into memory; use the curl script for very large videos.

## curl

List available models:

```bash
curl -sS "https://app.deepmark.me/client/models" -H "X-Client-Api-Key: $DEEPMARK_API_KEY" | python3 -m json.tool
```

Pass a model `_id` from the list and a binary watermark between its `min_watermark_length` and `max_watermark_length` (`""` for a zero-bit model):

```bash
./deepmark_quickstart.sh samples/speech.wav 6ab529a18d7eecb6f6d43f87 11001100110011001100110011001100
```

Requires bash, curl and Python 3.9+ on macOS, Linux or WSL. No Python packages are needed. Set `WAIT_MINUTES` to change the per-job wait limit (default 30).

Both quickstarts reuse their output filenames. If the media output is the input file, they use `watermarked_again` with the same extension.

## Callbacks

Run the receiver at a publicly reachable URL:

```bash
python callback_receiver.py 8080
```

Add `-F "callback_url=https://your-server.example.com/"` to the embed or detect request. The receiver saves results in `results/` and ignores repeated callbacks for the same job.

Callbacks are unsigned. The receiver downloads results by job ID using your API key to verify access.

## Adapting the examples

- **Model.** Use `GET /client/models` to choose an `_id` with the required `type`, `watermark_type` and watermark length range.
- **Payload.** The Python script generates random bits. Replace them with your own binary payload within the model's length range.
- **Content type.** Set the upload MIME type, such as `audio/wav` or `video/mp4`, to match the file. Both scripts infer it from the extension.

## More

See the [API Key Guide](https://www.deepmark.me/docs/api/key-guide) for request fields, result formats and errors.

## License

MIT. `samples/speech.wav` is a public-domain LibriVox recording.
