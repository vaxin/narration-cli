from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Dict, Optional
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


DEFAULT_API_URL = "https://api.minimaxi.com/v1/t2a_v2"
MAX_TEXT_CHARS = 9_999


class MiniMaxError(RuntimeError):
    """A safe, user-facing MiniMax request error."""


@dataclass(frozen=True)
class VoiceOptions:
    voice_id: str
    speed: float = 1.0
    volume: float = 1.0
    pitch: int = 0
    language_boost: Optional[str] = None


@dataclass(frozen=True)
class AudioOptions:
    sample_rate: int = 32_000
    bitrate: int = 128_000
    format: str = "mp3"
    channels: int = 1


class MiniMaxClient:
    def __init__(
        self,
        api_key: str,
        api_url: str = DEFAULT_API_URL,
        timeout: int = 180,
    ) -> None:
        self.api_key = api_key
        self.api_url = api_url
        self.timeout = timeout

    def synthesize(
        self,
        text: str,
        voice: VoiceOptions,
        model: str = "speech-2.8-hd",
        audio: AudioOptions = AudioOptions(),
    ) -> bytes:
        normalized = text.strip()
        if not normalized:
            raise MiniMaxError("input text is empty")
        if len(normalized) > MAX_TEXT_CHARS:
            raise MiniMaxError(
                f"input has {len(normalized)} characters; MiniMax requests must stay below 10000"
            )

        payload: Dict[str, Any] = {
            "model": model,
            "text": normalized,
            "stream": False,
            "output_format": "hex",
            "voice_setting": {
                "voice_id": voice.voice_id,
                "speed": voice.speed,
                "vol": voice.volume,
                "pitch": voice.pitch,
            },
            "audio_setting": {
                "sample_rate": audio.sample_rate,
                "bitrate": audio.bitrate,
                "format": audio.format,
                "channel": audio.channels,
            },
        }
        if voice.language_boost:
            payload["language_boost"] = voice.language_boost

        request = Request(
            self.api_url,
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )

        try:
            with urlopen(request, timeout=self.timeout) as response:
                raw = response.read()
        except HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")[:500]
            raise MiniMaxError(f"MiniMax HTTP {exc.code}: {detail}") from None
        except URLError as exc:
            raise MiniMaxError(f"could not connect to MiniMax: {exc.reason}") from None
        except TimeoutError:
            raise MiniMaxError("MiniMax request timed out") from None

        try:
            result = json.loads(raw)
        except (UnicodeDecodeError, json.JSONDecodeError):
            raise MiniMaxError("MiniMax returned an unreadable response") from None

        base_resp = result.get("base_resp") or {}
        status_code = base_resp.get("status_code", -1)
        if status_code != 0:
            message = base_resp.get("status_msg") or "unknown error"
            raise MiniMaxError(f"MiniMax error {status_code}: {message}")

        audio_hex = (result.get("data") or {}).get("audio")
        if not isinstance(audio_hex, str) or not audio_hex:
            raise MiniMaxError("MiniMax response did not contain audio data")
        try:
            return bytes.fromhex(audio_hex)
        except ValueError:
            raise MiniMaxError("MiniMax returned invalid audio data") from None
