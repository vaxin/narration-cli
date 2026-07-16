# narration-cli

A small command-line client for converting text to speech with the MiniMax API.

## Install

Python 3.9 or newer is required.

```bash
python3 -m pip install --user .
```

For development:

```bash
python3 -m pip install --user --editable .
```

Set credentials and a default voice locally:

```bash
export MINIMAX_API_KEY="your-api-key"
export NARRATE_VOICE_ID="your-voice-id"
```

Do not commit either value.

## Use

Convert inline text:

```bash
narrate text "Hello from the command line." -o output.mp3
```

Convert a UTF-8 text file. The default output is an MP3 beside the input file:

```bash
narrate file input.txt
```

Pass a voice for one invocation instead of setting `NARRATE_VOICE_ID`:

```bash
narrate text "Hello." --voice your-voice-id -o output.mp3
```

Preview a request without calling the API:

```bash
narrate text "Hello." --voice your-voice-id --dry-run -o output.mp3
```

Existing files are preserved unless `--force` is supplied.

```bash
narrate text "Replacement text." --voice your-voice-id --force -o output.mp3
```

Show all options:

```bash
narrate --help
narrate text --help
```

## Test

```bash
python3 -m unittest discover -v
```

The tests use a local HTTP stub and do not call MiniMax.
