#!/usr/bin/env bash
# Embed a watermark into a file, then detect it, with the DeepMark Client API and curl.
#
# Usage: ./deepmark_quickstart.sh <file> <model _id> <watermark bits>
#   ./deepmark_quickstart.sh samples/speech.wav 6ab529a18d7eecb6f6d43f87 11001100110011001100110011001100
# The watermark must have exactly the model's min_watermark_length bits; pass "" for a zero-bit model.
# Needs DEEPMARK_API_KEY in the environment. WAIT_MINUTES (default 30) caps the wait for each job.
set -euo pipefail

BASE_URL="https://app.deepmark.me"
: "${DEEPMARK_API_KEY:?set DEEPMARK_API_KEY first}"
[ $# -eq 3 ] || { sed -n '4,5p' "$0"; exit 2; }
FILE="$1"
MODEL_ID="$2"
WATERMARK="$3"
EXT="${FILE##*.}"

# curl uploads audio and video as application/octet-stream unless told the type, and the API rejects that.
content_type() {
  case "$(echo "${1##*.}" | tr '[:upper:]' '[:lower:]')" in
    wav) echo audio/wav ;;
    flac) echo audio/flac ;;
    mp3) echo audio/mpeg ;;
    ogg) echo audio/ogg ;;
    mp4) echo video/mp4 ;;
    mov) echo video/quicktime ;;
    webm) echo video/webm ;;
    png) echo image/png ;;
    jpg | jpeg) echo image/jpeg ;;
    *) echo "unsupported file type: $1" >&2; exit 2 ;;
  esac
}
TYPE="$(content_type "$FILE")"

job_id() {
  grep -o '"job_id": *"[^"]*"' "$1" | cut -d'"' -f4
}

# 400 means the job is not done yet; a 5xx can appear for a few seconds while the result is stored.
# Any other answer is final.
wait_for_result() {
  [ -n "$1" ] || { echo "no job ID, see the submit response above"; return 1; }
  for attempt in $(seq $((${WAIT_MINUTES:-30} * 12))); do
    read -r code RETURNED_TYPE < <(curl -sS -o "$2" -w "%{http_code} %{content_type}\n" \
      "$BASE_URL/client/inference-jobs/$1/download" \
      -H "X-Client-Api-Key: $DEEPMARK_API_KEY")
    [ "$code" = 200 ] && echo "saved $2" && return 0
    echo "$code $(cat "$2" 2>/dev/null)"
    rm -f "$2"
    case "$code" in
      400 | 5??) sleep 5 ;;
      *) return 1 ;;
    esac
  done
  echo "no result after ${WAIT_MINUTES:-30} minutes; run the wait again rather than resubmitting"
  return 1
}

echo "embedding $FILE with model $MODEL_ID"
curl -sS -X POST "$BASE_URL/client/embed" \
  -H "X-Client-Api-Key: $DEEPMARK_API_KEY" \
  -F "file=@$FILE;type=$TYPE" \
  -F "watermark=$WATERMARK" \
  -F "model=$MODEL_ID" | tee embed.json
echo
wait_for_result "$(job_id embed.json)" watermarked.download

# Name the file after what comes back: an MP3 upload returns WAV, for example.
case "${RETURNED_TYPE%%;*}" in
  audio/wav | audio/x-wav) OUT=watermarked.wav ;;
  audio/flac) OUT=watermarked.flac ;;
  audio/mpeg) OUT=watermarked.mp3 ;;
  video/mp4) OUT=watermarked.mp4 ;;
  image/png) OUT=watermarked.png ;;
  image/jpeg) OUT=watermarked.jpg ;;
  *) OUT="watermarked.$EXT" ;;
esac
mv watermarked.download "$OUT"
echo "renamed it $OUT"

echo "detecting the watermark in $OUT"
curl -sS -X POST "$BASE_URL/client/detect" \
  -H "X-Client-Api-Key: $DEEPMARK_API_KEY" \
  -F "file=@$OUT;type=$(content_type "$OUT")" \
  -F "model=$MODEL_ID" | tee detect.json
echo
wait_for_result "$(job_id detect.json)" result.json
cat result.json
echo
