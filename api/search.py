from http import HTTPStatus
from http.server import BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse

from web import api_core


class handler(BaseHTTPRequestHandler):
    def _send_json(self, payload: dict, status: HTTPStatus = HTTPStatus.OK):
        body = api_core.dumps_json(payload)
        self.send_response(status.value)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        params = parse_qs(urlparse(self.path).query)
        query = params.get("q", [""])[0].strip()
        kind = params.get("type", ["track"])[0]
        limit = int(params.get("limit", ["6"])[0])

        try:
            payload = api_core.search_metadata(query, kind=kind, limit=limit)
        except ValueError as exc:
            self._send_json({"error": str(exc)}, HTTPStatus.BAD_REQUEST)
            return
        except Exception as exc:
            self._send_json({"error": str(exc)}, HTTPStatus.BAD_GATEWAY)
            return

        self._send_json(payload)
