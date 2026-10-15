"""Receive DeepMark job callbacks and download results to ./results.

Pass this server's public URL as callback_url when submitting a job.

    python callback_receiver.py 8080

Needs DEEPMARK_API_KEY in the environment.
"""
import json
import os
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import requests

BASE_URL = "https://app.deepmark.me"
HEADERS = {"X-Client-Api-Key": os.environ["DEEPMARK_API_KEY"]}
RESULTS_DIR = "results"

seen_jobs = set()
seen_lock = threading.Lock()


def download(job_id, timeout=600, interval=5):
    """Retry downloads while the callback's result is being stored."""
    url = f"{BASE_URL}/client/inference-jobs/{job_id}/download"
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            response = requests.get(url, headers=HEADERS, timeout=300)
        except (requests.ConnectionError, requests.Timeout, requests.exceptions.ChunkedEncodingError):
            time.sleep(interval)
            continue
        if response.status_code == 200:
            disposition = response.headers.get("content-disposition", "")
            name = disposition.split('filename="')[-1].rstrip('"') if 'filename="' in disposition else job_id
            path = os.path.join(RESULTS_DIR, os.path.basename(name))
            with open(path, "wb") as f:
                f.write(response.content)
            print(f"job {job_id}: saved {path}")
            return
        if response.status_code != 400 and response.status_code < 500:
            print(f"job {job_id}: HTTP {response.status_code} {response.text}")
            return
        time.sleep(interval)
    print(f"job {job_id}: no result after {timeout} s")


class CallbackHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        body = self.rfile.read(int(self.headers.get("Content-Length") or 0))
        # Acknowledge before downloading; the result may not be stored yet.
        self.send_response(200)
        self.end_headers()
        try:
            event = json.loads(body)
        except ValueError:
            return
        job_id, status = event.get("job_id"), event.get("status")
        print(f"job {job_id}: {status} {event.get('error_message') or ''}".rstrip())
        if status != "completed" or not job_id:
            return
        with seen_lock:
            # Callbacks can be repeated.
            if job_id in seen_jobs:
                return
            seen_jobs.add(job_id)
        threading.Thread(target=download, args=(job_id,), daemon=True).start()

    def log_message(self, *args):
        pass


if __name__ == "__main__":
    os.makedirs(RESULTS_DIR, exist_ok=True)
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8080
    print(f"listening for DeepMark callbacks on port {port}")
    ThreadingHTTPServer(("", port), CallbackHandler).serve_forever()
