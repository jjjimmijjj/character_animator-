import whisper


#!/bin/bash

DIR=I:/REPOSITORY/completedaudio
OUTPUT=output.txt

FILES=$(find "$DIR" -name "*.wav")

# Debugging line: Print the files found by the find command
echo "Found audio files:"
echo "$FILES"

for FILE in $FILES; do
  echo "Transcribing $FILE..."
  whisper-stt "$FILE" >> "$OUTPUT"
done

echo "Done. The transcripts are in $OUTPUT."