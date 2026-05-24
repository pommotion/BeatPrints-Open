"""Small local web server for BeatPrints Open."""

from __future__ import annotations

import argparse
import json
import mimetypes
import os
import sys

from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, quote, unquote, urlparse


REPO_ROOT = Path(__file__).resolve().parents[1]
WORKSPACE_ROOT = REPO_ROOT.parent if (REPO_ROOT.parent / ".venv").exists() else REPO_ROOT
OUTPUT_DIR = WORKSPACE_ROOT / "output"
STATIC_DIR = Path(__file__).resolve().parent / "static"

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from web import api_core  # noqa: E402


class AppHandler(BaseHTTPRequestHandler):
    server_version = "BeatPrintsWeb/1.0"

    def log_message(self, fmt: str, *args):
        sys.stderr.write(f"[{self.log_date_time_string()}] {fmt % args}\n")

    def _send_json(self, payload: dict, status: HTTPStatus = HTTPStatus.OK):
        body = api_core.dumps_json(payload)
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

    def _send_png(self, data: bytes, filename: str):
        safe_filename = filename if filename.isascii() else "poster.png"
        encoded_filename = quote(filename)
        self.send_response(HTTPStatus.OK.value)
        self.send_header("Content-Type", "image/png")
        self.send_header("Content-Length", str(len(data)))
        self.send_header(
            "Content-Disposition",
            f"inline; filename=\"{safe_filename}\"; filename*=UTF-8''{encoded_filename}",
        )
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
                self._send_json(api_core.search_metadata(query, kind=kind, limit=limit))
            except Exception as exc:
                self._send_json({"error": str(exc)}, HTTPStatus.BAD_GATEWAY)
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
            try:
                self._send_json(api_core.lyrics_for_track(payload.get("track", {})))
            except Exception as exc:
                self._send_json({"error": str(exc)}, HTTPStatus.BAD_GATEWAY)
            return

        if parsed.path == "/api/generate":
            try:
                payload = self._read_json()
            except ValueError as exc:
                self._send_json({"error": str(exc)}, HTTPStatus.BAD_REQUEST)
                return
            try:
                png, filename = api_core.generate_poster_png(payload)
                self._send_png(png, filename)
            except ValueError as exc:
                self._send_json({"error": str(exc)}, HTTPStatus.BAD_REQUEST)
            except Exception as exc:
                self._send_json({"error": str(exc)}, HTTPStatus.BAD_GATEWAY)
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
