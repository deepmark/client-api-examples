# DeepMark Client API examples

Runnable examples for the [DeepMark Client API](https://www.deepmark.me/docs/api/key-guide): embed a
watermark into an audio, video or image file, then detect it, with an API key.

| File | What it does |
|---|---|
| `deepmark_quickstart.py` | Lists your models, embeds a random watermark of the right length with the one you choose, waits for the job, detects the watermark and prints the embedded and extracted bits. |
| `deepmark_quickstart.sh` | The same flow with curl, for a model and watermark you choose. |
| `callback_receiver.py` | A small web server that receives job callbacks and downloads each finished result. |
| `samples/speech.wav` | 11 seconds of public-domain speech from LibriVox (16 kHz mono) to try things with. |

## Before you start

You need an API key: sign in to the [DeepMark web app](https://app.deepmark.me/key), open **API Key** and click
**Generate API Key**. The key is shown once. No account yet? [Contact us](https://www.deepmark.me/contact).

```bash
export DEEPMARK_API_KEY="paste-your-api-key-here"
```

## Python

Python 3.9 or newer. On Debian and Ubuntu, install the venv module first (`sudo apt install python3-venv`).

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python deepmark_quickstart.py samples/speech.wav
```

Without a model `_id`, the script lists the models your key can use for that kind of file: their `_id`, name,
version, watermark length and type. Run it again with the `_id` of the model you want:

```bash
python deepmark_quickstart.py samples/speech.wav 6ab529a18d7eecb6f6d43f87
```

Output from a real API run on 2026-10-13 with a 32-bit audio model (repeated waiting lines omitted):

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

The script works the same way with image files (`.png`, `.jpg`) and an image model. It polls for up to 30 minutes
for each result; an in-progress request may finish later. It reads the whole file into memory;
for very large videos, use `deepmark_quickstart.sh`, which streams the upload.

## curl

List the models your key can use, and pick one:

```bash
curl -sS "https://app.deepmark.me/client/models" -H "X-Client-Api-Key: $DEEPMARK_API_KEY" | python3 -m json.tool
```

Note its `_id`, `min_watermark_length` and `max_watermark_length`, then run the script with a file, the `_id` and a
watermark of zeros and ones whose length is in that range (`""` for a zero-bit model):

```bash
./deepmark_quickstart.sh samples/speech.wav 6ab529a18d7eecb6f6d43f87 11001100110011001100110011001100
```

It needs bash, curl and Python 3.9+ (macOS, Linux, or WSL on Windows). Python's standard library checks the
detection JSON for a failed job; no Python packages are needed for this script. `WAIT_MINUTES` sets how long
it waits for each job (default 30).

Both quickstarts overwrite their previous output on a repeat run. If the output is also the input file,
they use `watermarked_again` with the same extension instead. A failed detection exits with its reason.

## Callbacks

Instead of polling, you can ask DeepMark to call your server when a job finishes. Run the receiver where
DeepMark can reach it:

```bash
python callback_receiver.py 8080
```

and add its URL to the embed or detection request, for example
`-F "callback_url=https://your-server.example.com/"`. The receiver answers each callback at once, downloads the
result of every completed job with your API key into `results/`, and ignores repeated callbacks for the same job.
Callbacks are not signed, so it only trusts what it can download with your key, and it builds the download URL
from the job ID instead of following any URL in the callback body.

## Adapting the examples

- **Your model.** Each organisation gets its own set of models. Pass the `_id` you want instead of relying on the
  default, and check its `type`, `watermark_type` and watermark length range in `GET /client/models`.
- **Your payload.** The examples embed random bits. In your system the bits identify something: a customer, a
  request, a piece of content. In Python, `format(customer_number, "032b")` turns a number into 32 bits, and
  `int(bits, 2)` turns extracted bits back into the number.
- **Polling or callbacks.** Polling is simplest; callbacks avoid repeated requests when you submit many jobs. Keep
  a timeout either way: a failed job answers `400 Result not available yet`, the same as a job still running.
- **Content types.** The API checks the upload's content type against the model's type. Both scripts set it from
  the file extension; if you write your own client, send `audio/wav`, `video/mp4` and so on, not
  `application/octet-stream`.

## More

The [API Key Guide](https://www.deepmark.me/docs/api/key-guide) covers every field, the detection result formats,
presigned downloads and the error messages.

## License

MIT. `samples/speech.wav` is a public-domain LibriVox recording.
