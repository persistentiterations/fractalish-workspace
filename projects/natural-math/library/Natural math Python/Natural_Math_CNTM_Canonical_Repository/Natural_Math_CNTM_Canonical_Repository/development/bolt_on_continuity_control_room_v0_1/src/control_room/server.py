"""Serve exactly one selected subject on localhost."""
from __future__ import annotations
import argparse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from .observer import DockerCliObserver
from .retention import capture_and_retain
from .comparison import compare_identity, generate_comparison_receipt
from .webapp import render_human_continuity, render_stage_four
from .transition import load as load_transition, classify as classify_transition
def serve(subject: str, evidence: str, count: int, port: int) -> None:
    observer = DockerCliObserver()
    document = capture_and_retain(observer, subject, Path(evidence), count)
    result = compare_identity(document)
    receipt = generate_comparison_receipt(document, result)
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            if self.path not in ("/", "/index.html"): self.send_error(404); return
            body = render_human_continuity(document, result, receipt).encode("utf-8")
            self.send_response(200); self.send_header("Content-Type", "text/html; charset=utf-8"); self.send_header("Content-Length", str(len(body))); self.send_header("Cache-Control", "no-store"); self.end_headers(); self.wfile.write(body)
        def log_message(self, format: str, *args: object) -> None: return
    print(f"Control Room retained {count} observations of {subject!r} at http://127.0.0.1:{port}")
    ThreadingHTTPServer(("127.0.0.1", port), Handler).serve_forever()
def main() -> None:
    parser = argparse.ArgumentParser(description="Read-only local Docker continuity page"); parser.add_argument("subject", help="exactly one container name or ID"); parser.add_argument("--evidence", required=True, help="operator-selected local evidence JSON path"); parser.add_argument("--transition-evidence"); parser.add_argument("--observations", type=int, default=2); parser.add_argument("--port", type=int, default=8765); arguments = parser.parse_args()
    if not arguments.transition_evidence: serve(arguments.subject, arguments.evidence, arguments.observations, arguments.port); return
    evidence = load_transition(Path(arguments.transition_evidence)); result = classify_transition(evidence)
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            body = render_stage_four(evidence, result).encode("utf-8"); self.send_response(200); self.send_header("Content-Type", "text/html; charset=utf-8"); self.send_header("Content-Length", str(len(body))); self.end_headers(); self.wfile.write(body)
        def log_message(self, format: str, *args: object) -> None: return
    ThreadingHTTPServer(("127.0.0.1", arguments.port), Handler).serve_forever()
if __name__ == "__main__": main()
