"""ローカル動作確認用サーバー。app.handler.handler をLambda Function URL相当のイベントでラップして呼ぶだけ。"""

import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import parse_qsl, urlsplit

from app.handler import handler

STATIC_DIR = Path(__file__).resolve().parent.parent / "static"


class DevHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/":
            self._serve_static("index.html")
        else:
            self._dispatch("GET")

    def do_POST(self):
        self._dispatch("POST")

    def do_OPTIONS(self):
        self._dispatch("OPTIONS")

    def _serve_static(self, filename: str) -> None:
        content = (STATIC_DIR / filename).read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(content)

    def _dispatch(self, method: str) -> None:
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length).decode("utf-8") if length else ""
        split = urlsplit(self.path)
        event = {
            "requestContext": {"http": {"method": method}},
            "rawPath": split.path,
            "queryStringParameters": dict(parse_qsl(split.query)),
            "body": body,
            "isBase64Encoded": False,
        }
        result = handler(event, None)
        self.send_response(result["statusCode"])
        for k, v in result.get("headers", {}).items():
            self.send_header(k, v)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "content-type")
        self.end_headers()
        body_out = result.get("body", "")
        if body_out:
            self.wfile.write(body_out.encode("utf-8"))


if __name__ == "__main__":
    port = 8000
    print(f"http://localhost:{port} で起動中...")
    HTTPServer(("0.0.0.0", port), DevHandler).serve_forever()
