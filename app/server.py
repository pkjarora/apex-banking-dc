"""
server.py — Pure-stdlib HTTP server for the Apex Banking DC app.
No third-party dependencies required.
"""

import os
import sys
import json
import mimetypes
import io
import urllib.parse
from http.server import BaseHTTPRequestHandler, HTTPServer
from socketserver import ThreadingMixIn

# -- path so database imports cleanly from any cwd --
HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import database as db

# Kubernetes metadata injected via Downward API env vars
CLUSTER_NAME = os.environ.get("CLUSTER_NAME", "k8s-dc-primary-cluster")
DATACENTER   = os.environ.get("DATACENTER", "Primary Datacenter")
DC_REGION    = os.environ.get("DC_REGION", "ap-south-1")
POD_NAME     = os.environ.get("POD_NAME", os.environ.get("HOSTNAME", "local"))
NODE_NAME    = os.environ.get("NODE_NAME", "k8s-node-01")
K8S_NS       = os.environ.get("K8S_NAMESPACE", "banking")
PORT         = int(os.environ.get("PORT", 8080))
STATIC_DIR   = os.path.join(HERE, "static")


# ---------------------------------------------------------------------------
# Handler
# ---------------------------------------------------------------------------
class Handler(BaseHTTPRequestHandler):

    def log_message(self, fmt, *args):
        pass  # suppress default access log noise

    def _send(self, status, body, ct="application/json"):
        if isinstance(body, (dict, list)):
            data = json.dumps(body).encode()
        elif isinstance(body, str):
            data = body.encode()
        else:
            data = body
        self.send_response(status)
        self.send_header("Content-Type", ct)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(data)

    def _body(self):
        n = int(self.headers.get("Content-Length", 0))
        if n == 0:
            return {}
        try:
            return json.loads(self.rfile.read(n))
        except Exception:
            return {}

    # ---- GET ---------------------------------------------------------------
    def do_GET(self):
        path = urllib.parse.urlparse(self.path).path

        if path == "/healthz":
            return self._send(200, "OK\n", "text/plain")

        if path == "/readyz":
            return self._send(200, "READY\n", "text/plain")

        if path == "/api/cluster":
            return self._send(200, {
                "cluster_name": CLUSTER_NAME,
                "datacenter":   DATACENTER,
                "region":       DC_REGION,
                "pod_name":     POD_NAME,
                "node_name":    NODE_NAME,
                "namespace":    K8S_NS,
            })

        if path == "/api/user":
            user = db.get_user("pankaj")
            return self._send(200 if user else 404, user or {"error": "not found"})

        if path == "/api/transactions":
            qs = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            limit = int(qs.get("limit", [50])[0])
            return self._send(200, db.get_transactions("pankaj", limit))

        # Static files
        if path in ("/", "/index.html"):
            return self._file(os.path.join(STATIC_DIR, "index.html"), "text/html")

        static_path = os.path.join(STATIC_DIR, path.lstrip("/"))
        if os.path.isfile(static_path):
            mime, _ = mimetypes.guess_type(static_path)
            return self._file(static_path, mime or "application/octet-stream")

        # SPA fallback
        return self._file(os.path.join(STATIC_DIR, "index.html"), "text/html")

    def _file(self, fpath, ct):
        if not os.path.isfile(fpath):
            return self._send(404, "Not found", "text/plain")
        with open(fpath, "rb") as f:
            data = f.read()
        self._send(200, data, ct)

    # ---- POST --------------------------------------------------------------
    def do_POST(self):
        path = urllib.parse.urlparse(self.path).path
        body = self._body()

        if path == "/api/transactions":
            try:
                txn = db.post_transaction(
                    username    = body.get("username", "pankaj"),
                    txn_type    = body.get("txn_type", "CREDIT"),
                    category    = body.get("category", "TRANSFER"),
                    description = body.get("description", ""),
                    amount      = float(body.get("amount", 0)),
                    cluster_name= CLUSTER_NAME,
                )
                user = db.get_user("pankaj")
                return self._send(200, {
                    "status":      "COMMITTED",
                    "transaction": txn,
                    "balance":     user["balance"],
                    "cluster":     CLUSTER_NAME,
                })
            except ValueError as e:
                return self._send(400, {"error": str(e)})

        if path == "/api/reset":
            db.reset(CLUSTER_NAME)
            return self._send(200, {"status": "RESET_OK"})

        return self._send(404, {"error": "Not found"})

    def do_OPTIONS(self):
        self._send(200, b"", "text/plain")


class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    daemon_threads = True


# ---------------------------------------------------------------------------
# Entry-point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    db.init_db()
    server = ThreadedHTTPServer(("0.0.0.0", PORT), Handler)
    print("=" * 60)
    print(f"  APEX BANKING — DC APPLICATION")
    print(f"  Cluster : {CLUSTER_NAME}")
    print(f"  Datacenter: {DATACENTER} ({DC_REGION})")
    print(f"  Listening: http://0.0.0.0:{PORT}")
    print(f"  User     : pankaj (Pankaj Arora)")
    print("=" * 60)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
