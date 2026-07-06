"""Tiny local HTTP server for the trading dashboard."""

from __future__ import annotations

from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
from urllib.parse import urlparse

from okx_quant.dashboard.data import DashboardConfig, load_dashboard_snapshot


STATIC_DIR = Path(__file__).with_name("static")


@dataclass(frozen=True)
class DashboardServerConfig:
    host: str
    port: int
    dashboard: DashboardConfig


def run_dashboard_server(config: DashboardServerConfig) -> None:
    handler = build_handler(config.dashboard)
    server = ThreadingHTTPServer((config.host, config.port), handler)
    try:
        print(f"http://{config.host}:{config.port}", flush=True)
        server.serve_forever()
    finally:
        server.server_close()


def build_handler(config: DashboardConfig):
    class DashboardHandler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802
            parsed = urlparse(self.path)
            if parsed.path == "/api/status":
                self._send_json(load_dashboard_snapshot(config))
                return
            if parsed.path in {"/", "/index.html"}:
                self._send_static("index.html", "text/html; charset=utf-8")
                return
            if parsed.path == "/app.css":
                self._send_static("app.css", "text/css; charset=utf-8")
                return
            if parsed.path == "/app.js":
                self._send_static("app.js", "application/javascript; charset=utf-8")
                return
            self.send_error(404)

        def log_message(self, format: str, *args: object) -> None:
            return

        def _send_json(self, payload: dict[str, object]) -> None:
            body = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _send_static(self, name: str, content_type: str) -> None:
            path = STATIC_DIR / name
            body = path.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    return DashboardHandler
