from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Optional


ROOT = Path(__file__).resolve().parents[1]


class _MiniMaxStub(BaseHTTPRequestHandler):
    requests: list[dict] = []

    def do_POST(self) -> None:  # noqa: N802 - stdlib handler API
        length = int(self.headers["Content-Length"])
        payload = json.loads(self.rfile.read(length))
        type(self).requests.append(
            {
                "path": self.path,
                "authorization": self.headers.get("Authorization"),
                "payload": payload,
            }
        )
        body = json.dumps(
            {
                "data": {"audio": b"fake-audio".hex()},
                "base_resp": {"status_code": 0, "status_msg": "success"},
            }
        ).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: object) -> None:
        pass


class NarrateCliTests(unittest.TestCase):
    def setUp(self) -> None:
        _MiniMaxStub.requests = []
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), _MiniMaxStub)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self) -> None:
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()

    def run_cli(
        self,
        *args: str,
        api_key: Optional[str] = "test-key",
        default_voice: Optional[str] = None,
    ) -> subprocess.CompletedProcess:
        env = os.environ.copy()
        env["PYTHONPATH"] = str(ROOT / "src")
        env["MINIMAX_API_URL"] = (
            f"http://127.0.0.1:{self.server.server_port}/v1/t2a_v2"
        )
        if api_key is None:
            env.pop("MINIMAX_API_KEY", None)
        else:
            env["MINIMAX_API_KEY"] = api_key
        if default_voice is None:
            env.pop("NARRATE_VOICE_ID", None)
        else:
            env["NARRATE_VOICE_ID"] = default_voice
        return subprocess.run(
            [sys.executable, "-m", "narration_cli", *args],
            cwd=ROOT,
            env=env,
            text=True,
            capture_output=True,
            check=False,
        )

    def test_text_writes_audio_with_requested_voice(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "output.mp3"
            result = self.run_cli(
                "text", "Test audio.", "--voice", "test-voice", "-o", str(output)
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(output.read_bytes(), b"fake-audio")
            request = _MiniMaxStub.requests[0]
            self.assertEqual(request["authorization"], "Bearer test-key")
            self.assertEqual(request["payload"]["model"], "speech-2.8-hd")
            self.assertEqual(request["payload"]["voice_setting"]["voice_id"], "test-voice")
            self.assertEqual(request["payload"]["voice_setting"]["speed"], 1.0)

    def test_file_uses_matching_output_name(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "input.txt"
            source.write_text("Test from a file.", encoding="utf-8")

            result = self.run_cli("file", str(source), default_voice="test-voice")

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(source.with_suffix(".mp3").read_bytes(), b"fake-audio")

    def test_dry_run_does_not_require_key_or_call_api(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "dry.mp3"
            result = self.run_cli(
                "text",
                "Preview only.",
                "--voice",
                "test-voice",
                "-o",
                str(output),
                "--dry-run",
                api_key=None,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("dry-run", result.stdout)
            self.assertFalse(output.exists())
            self.assertEqual(_MiniMaxStub.requests, [])

    def test_existing_output_is_preserved_without_force(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "safe.mp3"
            output.write_bytes(b"keep-me")

            result = self.run_cli(
                "text", "New text.", "--voice", "test-voice", "-o", str(output)
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("already exists", result.stderr)
            self.assertEqual(output.read_bytes(), b"keep-me")
            self.assertEqual(_MiniMaxStub.requests, [])

    def test_missing_api_key_has_actionable_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result = self.run_cli(
                "text",
                "Test.",
                "--voice",
                "test-voice",
                "-o",
                str(Path(tmp) / "output.mp3"),
                api_key=None,
            )

            self.assertEqual(result.returncode, 2)
            self.assertIn("MINIMAX_API_KEY", result.stderr)

    def test_missing_voice_has_actionable_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result = self.run_cli(
                "text", "Test.", "-o", str(Path(tmp) / "output.mp3")
            )

            self.assertEqual(result.returncode, 2)
            self.assertIn("NARRATE_VOICE_ID", result.stderr)


if __name__ == "__main__":
    unittest.main()
