---
name: narration-cli
description: Convert inline text or UTF-8 text files to speech with the installed `narrate` command and MiniMax API. Use when the user asks to generate a voice-over, create an audio file from text, preview a TTS request, select a MiniMax model or voice, adjust speech speed, or safely replace an existing output.
---

# Narration CLI

Use `narrate` as the TTS entry point. Do not recreate its HTTP request in an ad hoc script.

## Check prerequisites

1. Run `narrate --version`.
2. If unavailable, install this repository:

   ```bash
   python3 -m pip install --user --editable .
   ```

3. Verify required environment variables without printing their values:

   ```bash
   test -n "${MINIMAX_API_KEY:-}"
   test -n "${NARRATE_VOICE_ID:-}"
   ```

Never echo, log, commit, or place the API key on the command line.

## Generate audio

Convert inline text:

```bash
narrate text "Text to synthesize." -o output.mp3
```

Convert a UTF-8 text file:

```bash
narrate file input.txt
```

Override the default voice or request settings only when needed:

```bash
narrate text "Text to synthesize." \
  --voice your-voice-id \
  --model speech-2.8-hd \
  --speed 1.0 \
  -o output.mp3
```

Use `--dry-run` to inspect the request plan without calling the API:

```bash
narrate text "Text to synthesize." --voice your-voice-id --dry-run -o output.mp3
```

Do not use `--force` unless the user explicitly wants an existing file replaced.

## Verify output

1. Confirm the MP3 exists and is non-empty.
2. Use `ffprobe` when available to confirm it is readable and obtain its duration.
3. Report the output path and any failure without exposing credentials.

Keep each request below 10,000 characters. Split longer text at semantic paragraph boundaries and generate stable, ordered filenames.

## Handle failures

- Missing key: ask the user to set `MINIMAX_API_KEY` locally.
- Missing voice: ask the user to set `NARRATE_VOICE_ID` or pass `--voice`.
- Existing output: preserve it unless replacement was explicitly requested.
- API or network failure: retain any completed output and report the error without credentials.
