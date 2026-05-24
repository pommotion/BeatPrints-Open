import json

from http import HTTPStatus
from http.server import BaseHTTPRequestHandler
from urllib.parse import quote

from web import api_core


class handler(BaseHTTPRequestHandler):
    def _send_json(self, payload: dict, status: HTTPStatus = HTTPStatus.OK):
        body = api_core.dumps_json(payload)
        self.send_response(status.value)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

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

    def do_POST(self):
        try:
            payload = self._read_json()
            png, filename = api_core.generate_poster_png(payload)
        except ValueError as exc:
            self._send_json({"error": str(exc)}, HTTPStatus.BAD_REQUEST)
            return
        except Exception as exc:
            self._send_json({"error": str(exc)}, HTTPStatus.BAD_GATEWAY)
            return

        self._send_png(png, filename)
