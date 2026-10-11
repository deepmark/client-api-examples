"""Embed a watermark into a file, then detect it, with the DeepMark Client API.

Usage: python deepmark_quickstart.py <file> <model _id>
Without a model _id, it lists the models your key can use for that kind of file.
"""
import mimetypes
import os
import random
import sys
import time

import requests

BASE_URL = "https://app.deepmark.me"
HEADERS = {"X-Client-Api-Key": os.environ["DEEPMARK_API_KEY"]}
CONTENT_TYPES = {
    ".wav": "audio/wav", ".flac": "audio/flac", ".mp3": "audio/mpeg", ".ogg": "audio/ogg",
    ".mp4": "video/mp4", ".mov": "video/quicktime", ".webm": "video/webm",
    ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
}


def check(response):
    """Raise with the API's error message instead of a bare status code."""
    if not response.ok:
        raise RuntimeError(f"HTTP {response.status_code}: {response.text}")
    return response


def content_type_of(path):
    extension = os.path.splitext(path)[1].lower()
    return CONTENT_TYPES.get(extension) or mimetypes.guess_type(path)[0] or "application/octet-stream"


def submit(endpoint, path, **fields):
    """Upload a file to /client/embed or /client/detect and return the job ID."""
    with open(path, "rb") as f:
        files = {"file": (os.path.basename(path), f, content_type_of(path))}
        response = requests.post(f"{BASE_URL}/client/{endpoint}", headers=HEADERS,
                                 files=files, data=fields, timeout=300)
    return check(response).json()["job_id"]


def wait_for_result(job_id, timeout=1800, interval=5):
    """Poll the download endpoint until the job's result is ready."""
    url = f"{BASE_URL}/client/inference-jobs/{job_id}/download"
    deadline = time.monotonic() + timeout
    while True:
        response = requests.get(url, headers=HEADERS, timeout=300)
        if response.status_code == 200:
            return response
        # 400: not finished yet. 5xx: the result is still being stored, or a passing server error.
        # Anything else is final.
        if response.status_code != 400 and response.status_code < 500:
            check(response)
        if time.monotonic() > deadline:
            raise TimeoutError(f"job {job_id}: no result after {timeout} s "
                               f"(last answer: HTTP {response.status_code} {response.text[:200]})")
        time.sleep(interval)


path = sys.argv[1]
kind = content_type_of(path).split("/")[0]
models = check(requests.get(f"{BASE_URL}/client/models", headers=HEADERS, timeout=60)).json()
model = next((m for m in models if len(sys.argv) > 2 and m["_id"] == sys.argv[2]), None)
if model is None:
    print(f"Your {kind} models (pass one _id as the second argument):")
    for m in models:
        if m["type"] == kind:
            print(f"  {m['_id']}  {m['name']} {m['version']}, {m['min_watermark_length'] or 0}-bit {m['watermark_type']}")
    sys.exit(1)
print(f"model: {model['name']} {model['version']}")

# A multi-bit model takes exactly min_watermark_length bits; a zero-bit model takes none.
bits = "".join(random.choice("01") for _ in range(model["min_watermark_length"] or 0))

job_id = submit("embed", path, model=model["_id"], watermark=bits)
print("embed job:", job_id)
watermarked = wait_for_result(job_id)
# Name the file after what comes back: an MP3 upload returns WAV, for example.
returned_type = watermarked.headers.get("Content-Type", "").split(";")[0]
extension = next((e for e, t in CONTENT_TYPES.items() if t == returned_type), os.path.splitext(path)[1])
output_path = "watermarked" + extension
with open(output_path, "wb") as f:
    f.write(watermarked.content)
print("saved", output_path)

job_id = submit("detect", output_path, model=model["_id"])
print("detect job:", job_id)
result = wait_for_result(job_id).json()
print("watermark found:", result["decision"])
if result.get("extracted_watermark"):
    print("embedded: ", bits)
    print("extracted:", "".join(map(str, result["extracted_watermark"])))
