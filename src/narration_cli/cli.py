from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import Optional, Sequence

from narration_cli import __version__
from narration_cli.minimax import DEFAULT_API_URL, MiniMaxClient, MiniMaxError, VoiceOptions


class CliError(RuntimeError):
    pass


def _common_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument(
        "--voice",
        help="MiniMax voice_id; defaults to NARRATE_VOICE_ID",
    )
    parser.add_argument("--model", default="speech-2.8-hd")
    parser.add_argument("--speed", type=float, default=1.0)
    parser.add_argument("--language-boost")
    parser.add_argument("--dry-run", action="store_true", help="print the plan without calling the API")
    parser.add_argument("--force", action="store_true", help="replace an existing output file")
    return parser


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="narrate",
        description="Convert text to speech with MiniMax.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    subparsers = parser.add_subparsers(dest="command", required=True)
    common = _common_parser()

    text_parser = subparsers.add_parser(
        "text", parents=[common], help="convert inline text to one audio file"
    )
    text_parser.add_argument("text")
    text_parser.add_argument("-o", "--output", type=Path, default=Path("output.mp3"))

    file_parser = subparsers.add_parser(
        "file", parents=[common], help="convert a UTF-8 text file to one audio file"
    )
    file_parser.add_argument("input", type=Path)
    file_parser.add_argument("-o", "--output", type=Path)
    return parser


def _voice_options(args: argparse.Namespace) -> VoiceOptions:
    voice_id = (args.voice or os.environ.get("NARRATE_VOICE_ID", "")).strip()
    if not voice_id:
        raise CliError("set NARRATE_VOICE_ID or pass --voice")
    return VoiceOptions(
        voice_id=voice_id,
        speed=args.speed,
        language_boost=args.language_boost,
    )


def _client() -> MiniMaxClient:
    api_key = os.environ.get("MINIMAX_API_KEY", "").strip()
    if not api_key:
        raise CliError("set the MINIMAX_API_KEY environment variable")
    api_url = os.environ.get("MINIMAX_API_URL", DEFAULT_API_URL).strip()
    return MiniMaxClient(api_key=api_key, api_url=api_url)


def _ensure_writable(output: Path, force: bool) -> None:
    if output.exists() and not force:
        raise CliError(f"output already exists: {output} (use --force to replace it)")


def _write_atomic(output: Path, audio: bytes) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_name(f".{output.name}.part")
    try:
        temporary.write_bytes(audio)
        temporary.replace(output)
    finally:
        temporary.unlink(missing_ok=True)


def _generate(text: str, output: Path, args: argparse.Namespace) -> None:
    normalized = text.strip()
    if not normalized:
        raise CliError("input text is empty")
    output = output.expanduser().resolve()
    _ensure_writable(output, args.force)
    voice = _voice_options(args)
    print(
        f"Input: {len(normalized)} characters\n"
        f"Output: {output}\n"
        f"Model: {args.model} | Voice: {voice.voice_id} | Speed: {voice.speed}"
    )
    if args.dry_run:
        print("dry-run: no API request was made and no file was written")
        return
    audio = _client().synthesize(normalized, voice=voice, model=args.model)
    _write_atomic(output, audio)
    print(f"Wrote {output} ({len(audio)} bytes)")


def _run_text(args: argparse.Namespace) -> None:
    _generate(args.text, args.output, args)


def _run_file(args: argparse.Namespace) -> None:
    source = args.input.expanduser().resolve()
    if not source.is_file():
        raise CliError(f"input file not found: {source}")
    output = args.output or source.with_suffix(".mp3")
    _generate(source.read_text(encoding="utf-8"), output, args)


def run(argv: Optional[Sequence[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "text":
            _run_text(args)
        elif args.command == "file":
            _run_file(args)
        else:
            parser.error(f"unknown command: {args.command}")
    except (CliError, MiniMaxError, UnicodeError, OSError) as exc:
        print(f"narrate: error: {exc}", file=sys.stderr)
        return 2
    return 0


def main() -> None:
    raise SystemExit(run())
