"""Small local web server for BeatPrints Open."""

from __future__ import annotations

import argparse
import json
import mimetypes
import os
import sys
import time

from dataclasses import asdict
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse


REPO_ROOT = Path(__file__).resolve().parents[1]
WORKSPACE_ROOT = REPO_ROOT.parent if (REPO_ROOT.parent / ".venv").exists() else REPO_ROOT
OUTPUT_DIR = WORKSPACE_ROOT / "output"
STATIC_DIR = Path(__file__).resolve().parent / "static"

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from BeatPrints import errors, lyrics, poster, spotify  # noqa: E402


SPOTIFY = spotify.Spotify()
LYRICS = lyrics.Lyrics()
POSTER = poster.Poster(str(OUTPUT_DIR))
THEMES = ["Light", "Dark", "Catppuccin", "Gruvbox", "Nord", "RosePine", "Everforest"]


def _json_default(value):
    if hasattr(value, "__dataclass_fields__"):
        return asdict(value)
    raise TypeError(f"Object of type {type(value).__name__} is not JSON serializable")


def _metadata_from_payload(payload: dict) -> spotify.TrackMetadata:
    required = ["name", "artist", "album", "released", "duration", "image", "label", "id"]
    data = {key: str(payload.get(key, "")) for key in required}
    return spotify.TrackMetadata(**data)


def _line_range(lines: list[str], start: int, end: int) -> str:
    cleaned = [line for line in lines if line.strip()]
    if len(cleaned) < 4:
        return "\n".join(cleaned)

    start = max(start, 1)
    end = min(end, len(cleaned))
    selected = cleaned[start - 1 : end]
    if len(selected) != 4:
        selected = cleaned[:4]
    return "\n".join(selected)


def _latest_created(before: set[Path]) -> Path | None:
    after = set(OUTPUT_DIR.glob("*.png"))
    created = after - before
    if not created:
        return None
    return max(created, key=lambda path: path.stat().st_mtime)


class AppHandler(BaseHTTPRequestHandler):
    server_version = "BeatPrintsWeb/1.0"

    def log_message(self, fmt: str, *args):
        sys.stderr.write(f"[{self.log_date_time_string()}] {fmt % args}\n")

    def _send_json(self, payload: dict, status: HTTPStatus = HTTPStatus.OK):
        body = json.dumps(payload, default=_json_default).encode("utf-8")
        self.send_response(status.value)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_file(self, path: Path):
        if not path.exists() or not path.is_file():
            self.send_error(HTTPStatus.NOT_FOUND.value)
            return

        content_type = mimetypes.guess_type(str(path))[0] or "application/octet-stream"
        data = path.read_bytes()
        self.send_response(HTTPStatus.OK.value)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _read_json(self) -> dict:
        length = int(self.headers.get("Content-Length", "0"))
        if length == 0:
            return {}
        try:
            return json.loads(self.rfile.read(length).decode("utf-8"))
        except json.JSONDecodeError as exc:
            raise ValueError("Invalid JSON request body.") from exc

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path

        if path == "/":
            self._send_file(STATIC_DIR / "index.html")
            return

        if path.startswith("/static/"):
            self._send_file(STATIC_DIR / unquote(path.removeprefix("/static/")))
            return

        if path.startswith("/output/"):
            self._send_file(OUTPUT_DIR / unquote(path.removeprefix("/output/")))
            return

        if path == "/api/search":
            params = parse_qs(parsed.query)
            query = params.get("q", [""])[0].strip()
            kind = params.get("type", ["track"])[0]
            limit = int(params.get("limit", ["6"])[0])

            if not query:
                self._send_json({"error": "Search query is required."}, HTTPStatus.BAD_REQUEST)
                return

            try:
                if kind == "album":
                    results = SPOTIFY.get_album(query, limit=limit)
                else:
                    results = SPOTIFY.get_track(query, limit=limit)
            except (errors.NoMatchingTrackFound, errors.NoMatchingAlbumFound):
                self._send_json({"results": []})
                return
            except Exception as exc:
                self._send_json({"error": str(exc)}, HTTPStatus.BAD_GATEWAY)
                return

            self._send_json({"results": results})
            return

        self.send_error(HTTPStatus.NOT_FOUND.value)

    def do_POST(self):
        parsed = urlparse(self.path)

        if parsed.path == "/api/lyrics":
            try:
                payload = self._read_json()
            except ValueError as exc:
                self._send_json({"error": str(exc)}, HTTPStatus.BAD_REQUEST)
                return
            track = _metadata_from_payload(payload.get("track", {}))

            try:
                text, source = LYRICS.get_lyrics_with_source(track)
                lines = [line for line in text.splitlines() if line.strip()]
                self._send_json({"lyrics": text, "lines": lines, "source": source})
            except errors.NoLyricsAvailable:
                self._send_json(
                    {
                        "lyrics": "",
                        "lines": [],
                        "source": "",
                        "warning": "No lyrics found. Enter custom lyrics to generate a poster.",
                    }
                )
            except Exception as exc:
                self._send_json({"error": str(exc)}, HTTPStatus.BAD_GATEWAY)
            return

        if parsed.path == "/api/generate":
            try:
                payload = self._read_json()
            except ValueError as exc:
                self._send_json({"error": str(exc)}, HTTPStatus.BAD_REQUEST)
                return
            track = _metadata_from_payload(payload.get("track", {}))
            theme = payload.get("theme", "Light")
            accent = bool(payload.get("accent", False))
            custom_lyrics = str(payload.get("customLyrics", "")).strip()
            lines = payload.get("lines") or []
            start = int(payload.get("start", 1))
            end = int(payload.get("end", 4))

            if theme not in THEMES:
                self._send_json({"error": "Invalid theme."}, HTTPStatus.BAD_REQUEST)
                return

            selected = custom_lyrics or _line_range(lines, start, end)
            if not selected:
                self._send_json(
                    {"error": "Select lyrics or enter custom lyrics."},
                    HTTPStatus.BAD_REQUEST,
                )
                return

            OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
            before = set(OUTPUT_DIR.glob("*.png"))

            try:
                POSTER.track(track, selected, accent=accent, theme=theme)
            except Exception as exc:
                self._send_json({"error": str(exc)}, HTTPStatus.BAD_GATEWAY)
                return

            time.sleep(0.05)
            created = _latest_created(before)
            if created is None:
                self._send_json({"error": "Poster was generated but no output file was found."})
                return

            self._send_json(
                {
                    "image": f"/output/{created.name}",
                    "filename": created.name,
                    "lyrics": selected,
                }
            )
            return

        self.send_error(HTTPStatus.NOT_FOUND.value)


def main():
    parser = argparse.ArgumentParser(description="Run the BeatPrints Open web UI.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", default=int(os.getenv("PORT", "8010")), type=int)
    args = parser.parse_args()

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    server = ThreadingHTTPServer((args.host, args.port), AppHandler)
    print(f"BeatPrints Open web UI running at http://{args.host}:{args.port}")
    server.serve_forever()


if __name__ == "__main__":
    main()
