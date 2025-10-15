# mitmdump -s super_simple_forwarder.py -p 8080
from mitmproxy import http
import json, base64, re
from urllib.parse import urlparse

ALLOWED_HOSTS = {"localhost", "127.0.0.1"}   # restrict to local dev
INCLUDE_PATHS = ("/api/", "/rest/")          # less noise

def _b64(b): return base64.b64encode(b).decode("ascii") if b else ""
def _norm(path):
    path = re.sub(r'/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}', '/{uuid}', path, flags=re.I)
    return re.sub(r'/\d+', '/{id}', path)

def response(flow: http.HTTPFlow):
    req, resp = flow.request, flow.response
    if not resp: return
    host = (urlparse(req.pretty_url).hostname or "").lower()
    if not any(h in host for h in ALLOWED_HOSTS): return
    if not any(req.path.startswith(p) for p in INCLUDE_PATHS): return

  
    headers = {k:v for k,v in req.headers.items() if k.lower() not in ("cookie","authorization","content-length")}
    rec = {
        "method": req.method,
        "url": req.pretty_url,
        "path_template": _norm(req.path),
        "headers": headers,
        "body_b64": _b64(req.raw_content or b""),
        "status": resp.status_code,
    }
    with open("captures.jsonl", "a", encoding="utf-8") as f:
        f.write(json.dumps(rec) + "\n")
