#!/bin/bash
# ==============================================================================
# CiSAI Video Optimization Tool: 4K UHD to 1080p Full HD Transcoder
# Prevents LG webOS TV hardware video decoder buffer overflows
# ==============================================================================

set -e

SRC_DIR="media_4k_backup"
DEST_DIR="media"

mkdir -p "$SRC_DIR"
mkdir -p "$DEST_DIR"

echo "=== Optimizing Corporate Videos for Smart TV Playback (1080p H.264) ==="

for src_file in "$SRC_DIR"/*.mp4; do
  [ -e "$src_file" ] || continue
  filename=$(basename "$src_file")
  tmp_file="$DEST_DIR/${filename}.opt.mp4"
  dest_file="$DEST_DIR/$filename"

  echo "Transcoding: $filename -> 1080p..."
  ffmpeg -y -hide_banner -loglevel warning \
    -i "$src_file" \
    -vf "scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2" \
    -c:v libx264 -preset fast -crf 21 \
    -pix_fmt yuv420p \
    -movflags +faststart \
    -c:a aac -b:a 128k \
    "$tmp_file"

  mv -f "$tmp_file" "$dest_file"
  echo "Completed: $dest_file ($(du -h "$dest_file" | cut -f1))"
done

echo "=== All videos successfully optimized to 1080p Full HD ==="
