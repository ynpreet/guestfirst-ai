#!/usr/bin/env python3
"""GuestFirst AI -- localhost web UI (stdlib only).

Run:  python3 app.py   then open http://localhost:8008
Serves a guided, personalized tour of demo.py (the tested artifact --
demo.py is never modified here; it is only imported as a module and its
canned subprocess run is unchanged).
"""

import contextlib
import http.server
import io
import json
import mimetypes
import re
import subprocess
import sys
import urllib.parse
from pathlib import Path

HOST = "127.0.0.1"
PORT = 8008
HERE = Path(__file__).resolve().parent
DEMO_PY = HERE / "demo.py"

sys.path.insert(0, str(HERE))
import demo as DEMO  # the tested artifact: imported, never modified

COND_RE = re.compile(
    r"(type 2 diabetes|type 1 diabetes|diabetes|hypertension|high blood pressure|"
    r"kidney disease|ckd|heart disease|depression|asthma|arthritis|copd|hyperlipidemia)"
)

def _capture_canned():
    """Run the canned demo exactly as before (subprocess), capture stdout."""
    proc = subprocess.run(
        [sys.executable, str(DEMO_PY)],
        cwd=str(HERE),
        capture_output=True,
        text=True,
        timeout=600,
    )
    return proc.stdout or proc.stderr

def _capture_fn(fn, params):
    buf = io.StringIO()
    try:
        with contextlib.redirect_stdout(buf):
            return fn(params)
    except Exception as exc:  # never crash the page on a bad input
        return "[web-ui] The personalized run hit an error and stopped safely.\n%s: %s" % (type(exc).__name__, exc)

# ---- personalized run: input handling lives in app.py; demo.py untouched ----

_GF_LABELS = {
    "long_wait": "long wait times",
    "missing_items": "missing items",
    "incorrect_orders": "incorrect orders",
    "delivery_delay": "delivery delays",
}

def run_custom(params):
    cat = (params.get("category") or "long_wait").strip()
    if cat not in _GF_LABELS:
        cat = "long_wait"
    orders, complaints, pickup_records = DEMO.build_world()
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        mine = [c for c in complaints if c["category"] == cat]
        print(f"YOUR COMPLAINT: customers report {_GF_LABELS[cat]} -- {len(mine)} such complaints today.")
        print("The agent investigates YOUR category first, then decides which data to inspect.")
        print()
        counts = DEMO.t_categorize_complaints(complaints)
        print("Full-day complaint mix:", counts)
        conc = DEMO.t_complaint_concentration(complaints, cat)
        peak = {b: conc.get(b, 0) for b in DEMO.BUCKETS if conc.get(b, 0)}
        print(f"Concentration of '{cat}' by bucket:", peak)
        today, base, peak_today, peak_base = DEMO.t_compare_volume()
        print(f"Volume context: {today} orders today vs {base} baseline; peak {peak_base} -> {peak_today}.")
        if mine:
            c = mine[0]
            print()
            print(f"Zooming into one of yours: {c['id']} -- \"{c['text']}\" (order {c['order_id']})")
            print("Order lookup:", DEMO.t_lookup_order(orders, c["order_id"]))
            print("Pickup verification:", DEMO.t_verify_pickup(pickup_records, c["order_id"]))
            action = "replacement + $5 coupon"
            print("Recovery policy:", DEMO.t_check_recovery_policy(action))
            print("Manager approval:", DEMO.t_request_approval(action, "store manager"))
        print()
        print("Same investigate -> recover -> verify loop, aimed at YOUR complaint type.")
    return out.getvalue()

PAGE = '<!DOCTYPE html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n<meta name="viewport" content="width=device-width, initial-scale=1">\n<title>GuestFirst AI &mdash; Live Demo</title>\n<style>\n:root{\n  --bg:#0b1220; --bg2:#0e1626; --panel:#131e33; --panel2:#182742;\n  --ink:#eaf0f9; --muted:#9db0c9; --faint:#6b7f99;\n  --teal:#2dd4bf; --teal-dim:rgba(45,212,191,.12);\n  --accent:#5aa9ff; --warn:#fbbf24; --danger:#f87171; --ok:#34d399;\n  --line:#233451; --radius:14px;\n}\n*{box-sizing:border-box}\nbody{margin:0;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;\n  background:var(--bg);color:var(--ink);line-height:1.6}\nheader{background:linear-gradient(135deg,#0a2540 0%,#0e3a5c 60%,#0b4f4a 100%);\n  padding:42px 32px 34px;border-bottom:1px solid var(--line)}\n.wrap{max-width:1060px;margin:0 auto}\nheader h1{margin:0 0 8px;font-size:30px;letter-spacing:-.01em}\nheader .sub{margin:0;color:#c8d6ea;font-size:16px;max-width:800px}\n.badge{display:inline-block;margin-top:14px;font-size:11.5px;letter-spacing:.1em;\n  text-transform:uppercase;color:#06281f;background:var(--teal);\n  padding:5px 14px;border-radius:999px;font-weight:800}\nmain{padding:8px 32px 48px}\nsection.card{background:var(--panel);border:1px solid var(--line);\n  border-radius:var(--radius);padding:26px 28px;margin:26px 0}\nsection.card h2{margin:0 0 12px;font-size:18px;color:var(--teal)}\nsection.card h2 .n{display:inline-block;width:28px;height:28px;border-radius:50%;\n  background:var(--teal-dim);border:1px solid var(--teal);color:var(--teal);\n  text-align:center;line-height:26px;font-size:14px;margin-right:10px}\nsection.card p{margin:0 0 12px;color:#d5e0f1;font-size:15.5px}\nsection.card p:last-child{margin-bottom:0}\n.watch{list-style:none;margin:6px 0 0;padding:0}\n.watch li{position:relative;padding:8px 0 8px 30px;color:#d5e0f1;font-size:15px;\n  border-bottom:1px dashed var(--line)}\n.watch li:last-child{border-bottom:0}\n.watch li::before{content:"\\25b8";position:absolute;left:8px;color:var(--teal);font-weight:700}\nlabel.f{display:block;margin:14px 0 6px;font-size:13px;font-weight:700;\n  letter-spacing:.04em;text-transform:uppercase;color:var(--muted)}\ninput[type=text],input[type=number],select,textarea{\n  width:100%;background:var(--bg2);border:1px solid var(--line);color:var(--ink);\n  border-radius:10px;padding:11px 14px;font-size:15px;font-family:inherit}\ntextarea{min-height:76px;resize:vertical}\ninput:focus,select:focus,textarea:focus{outline:none;border-color:var(--teal)}\n.row2{display:grid;grid-template-columns:1fr 1fr;gap:14px}\n@media(max-width:700px){.row2{grid-template-columns:1fr}}\n.btnrow{display:flex;gap:14px;align-items:center;margin-top:20px;flex-wrap:wrap}\nbutton.run{background:linear-gradient(135deg,#14b8a6,#0d9488);border:0;\n  color:#04211c;font-weight:800;font-size:17px;padding:15px 34px;\n  border-radius:12px;cursor:pointer;box-shadow:0 6px 22px rgba(45,212,191,.25)}\nbutton.run:hover{filter:brightness(1.08)}\nbutton.run:disabled{opacity:.45;cursor:default;box-shadow:none}\nbutton.ghost{background:transparent;border:1px solid var(--teal);color:var(--teal);\n  font-weight:700;font-size:15px;padding:13px 26px;border-radius:12px;cursor:pointer}\nbutton.ghost:hover{background:var(--teal-dim)}\nbutton.ghost:disabled{opacity:.45;cursor:default}\n.hint{color:var(--muted);font-size:13.5px}\n.spinner{display:none;align-items:center;gap:10px;color:var(--muted);font-size:14px;margin-top:14px}\n.spinner.show{display:flex}\n.dot{width:12px;height:12px;border-radius:50%;background:var(--teal);\n  animation:pulse 1s infinite ease-in-out}\n@keyframes pulse{0%,100%{transform:scale(.6);opacity:.5}50%{transform:scale(1.2);opacity:1}}\n#output{display:none;margin-top:6px}\n#output.show{display:block}\n.out{background:#0a0f1c;border:1px solid var(--line);border-radius:12px;\n  padding:20px 22px;font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;\n  font-size:13px;line-height:1.6;white-space:pre-wrap;word-wrap:break-word;\n  max-height:640px;overflow:auto;color:#c9d6ea}\n.sechead{color:var(--accent);font-weight:800;margin:18px 0 2px;font-size:13.5px}\n.sechead:first-child{margin-top:0}\n.seccap{background:var(--teal-dim);border-left:3px solid var(--teal);\n  padding:8px 12px;margin:4px 0 12px;border-radius:0 8px 8px 0;\n  font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;\n  font-size:13.5px;color:#bfe9e2}\n.tok-orch{color:var(--accent);font-weight:700}\n.tok-tool{color:var(--ok);font-weight:700}\n.tok-guard{color:var(--warn);font-weight:700}\n.tok-mem{color:#c084fc;font-weight:700}\n#takeaways{display:none}\n#takeaways.show{display:block}\n.take{background:rgba(52,211,153,.07);border:1px solid rgba(52,211,153,.4);\n  border-radius:var(--radius);padding:22px 26px;margin:26px 0}\n.take h2{color:var(--ok);margin:0 0 10px;font-size:18px}\n.take ul{margin:0;padding-left:20px}\n.take li{margin:8px 0;color:#d5e0f1;font-size:15px}\ntable.dec{width:100%;border-collapse:collapse;margin-top:12px;font-size:14px}\ntable.dec th{background:var(--panel2);color:var(--teal);text-align:left;\n  padding:10px 12px;font-size:12px;letter-spacing:.06em;text-transform:uppercase;\n  border-bottom:1px solid var(--line)}\ntable.dec td{padding:10px 12px;border-bottom:1px solid var(--line);vertical-align:top}\n.pill{display:inline-block;padding:3px 12px;border-radius:999px;font-weight:800;font-size:12px}\n.pill.v{background:var(--ok);color:#04281c}\n.pill.s{background:var(--faint);color:#0b1220}\nfooter{padding:26px 32px 40px;color:var(--faint);font-size:13.5px;text-align:center}\nfooter a{color:var(--teal);text-decoration:none}\nfooter a:hover{text-decoration:underline}\ndetails.raw{margin-top:14px}\ndetails.raw summary{cursor:pointer;color:var(--muted);font-size:13.5px}\n</style>\n</head>\n<body>\n<header><div class="wrap">\n  <h1>GuestFirst AI</h1>\n  <p class="sub">Friday lunch, complaints spiking. The agent finds the why, fixes it, and proves it.</p>\n</div></header>\n<main><div class="wrap">\n\n<section class="card" id="story">\n  <h2><span class="n">1</span>The story</h2>\n  <p>It\'s Friday lunch at TastePoint Downtown and complaints are spiking. A dashboard would say <i>“satisfaction declined 12%.”</i> A chatbot would say <i>“customers mention long wait times.”</i> Neither tells the manager what to <b>do</b>.</p>\n<p>GuestFirst is the agent that does: it categorizes the complaints, chooses which operational data to inspect <i>from the pattern</i>, tests three root-cause hypotheses while keeping correlation and causation strictly separate, recovers the affected customers within policy, forecasts demand — and verifies the fix with a simulation. Then the twist: a fryer goes offline tomorrow, and the agent replans under the new constraint <i>before</i> lunch.</p>\n</section>\n\n<section class="card" id="watch">\n  <h2><span class="n">2</span>What to watch for</h2>\n  <ul class="watch">\n<li>Watch the agent pick its own investigation path from the complaint pattern — not a generic data dump.</li>\n<li>The correlation trap: naive grill-volume correlation says r = −0.43 (wrong sign!). Watch the agent test the <i>mechanism</i> instead.</li>\n<li>The twist: a fryer goes offline. The agent replans under the new constraint and simulates both plans.</li>\n<li>The scoreboard: agent vs. fixed-staffing baseline on identical simulated data.</li>\n  </ul>\n</section>\n\n\n\n<section class="card" id="tryown">\n  <h2><span class="n">✎</span>Try your own</h2>\n  <p>Pick <b>your</b> complaint type — the agent will focus its investigation on it, same tools, same rules.</p>\n  <label class="f" for="u_cat">Complaint type</label>\n  <select id="u_cat">\n    <option value="long_wait">Long wait times</option>\n    <option value="missing_items">Missing items</option>\n    <option value="incorrect_orders">Incorrect orders</option>\n    <option value="delivery_delay">Delivery delays</option>\n  </select>\n  <div class="btnrow">\n    <button class="ghost" id="customRun">Investigate my complaint</button>\n    <span class="hint">Same inputs → same output. Deterministic.</span>\n  </div>\n  <div class="spinner" id="cspin"><div class="dot"></div>Investigating…</div>\n</section>\n\n\n<section class="card" id="runbox">\n  <h2><span class="n">3</span>Run the demo</h2>\n  <p>Click below to run the full canned demonstration. It takes a few seconds.</p>\n  <div class="btnrow">\n    <button class="run" id="run">&#9654; Run live demo</button>\n  </div>\n  <div class="spinner" id="spin"><div class="dot"></div><span>The agent is investigating the complaints…</span></div>\n  <div id="output">\n    <div class="out" id="outtext"></div>\n    <details class="raw"><summary>Show raw terminal output</summary>\n      <div class="out" id="rawtext"></div>\n    </details>\n  </div>\n</section>\n\n<section class="card" id="takeaways" style="display:none">\n  <div class="take">\n    <h2>What just happened</h2>\n    <ul>\n<li>Correlation lied (r = −0.43); the mechanism told the truth: grill arrivals exceeded capacity for 45 straight minutes.</li>\n<li>Staffing was explicitly NOT blamed — it never varied, and a constant can\'t explain a change.</li>\n<li>The twist proved agency: new constraint in, revised plan out, both simulated before lunch.</li>\n<li>Recovery was closed-loop: every affected customer tracked to resolution, not just apologized to.</li>\n<li>Try your own: pick a complaint type in “Try your own” and watch the investigation focus on it.</li>\n    </ul>\n  </div>\n</section>\n\n</div></main>\n<footer><div class="wrap">\n  <a href="https://github.com/ynpreet/guestfirst-ai" target="_blank" rel="noopener">View the project on GitHub</a>\n  &nbsp;&middot;&nbsp; All data in this demo is synthetic / fictional.\n</div></footer>\n\n<script>\nconst SECTIONS = [["STEP 1/6", "Categorize: what are customers actually complaining about?"], ["STEP 2/6", "Investigate: volume, timestamps, demand, staffing, inventory \\u2014 chosen from the pattern, not dumped generically."], ["STEP 3/6", "Root cause: three hypotheses tested, correlation separated from causation. The priority feature."], ["STEP 4/6", "Service recovery: one complaint handled end-to-end, within policy, with approval."], ["STEP 5/6", "Coordinate: demand forecast, kitchen check, the adjusted plan."], ["STEP 6/6", "Verify: simulation compares original vs. revised plan before the next rush."], ["EVALUATION", "Agent vs. baseline on identical data \\u2014 simulated outcomes, labeled as such."], ["WHY AN AGENT", "The closing argument: what a dashboard and a chatbot would have said instead."]];\nfunction esc(s){return s.replace(/&/g,\'&amp;\').replace(/</g,\'&lt;\').replace(/>/g,\'&gt;\');}\nfunction decorate(line){\n  let h = esc(line);\n  h = h.replace(/\\[ORCHESTRATOR\\]/g,\'<span class="tok-orch">[ORCHESTRATOR]</span>\');\n  h = h.replace(/\\[TOOL [^\\]]+\\]/g,function(m){return \'<span class="tok-tool">\'+m+\'</span>\';});\n  h = h.replace(/\\[MEMORY\\]/g,\'<span class="tok-mem">[MEMORY]</span>\');\n  h = h.replace(/GUARDRAIL/g,\'<span class="tok-guard">GUARDRAIL</span>\');\n  return h;\n}\nfunction renderOut(text){\n  document.getElementById(\'rawtext\').textContent = text;\n  const lines = text.split(\'\\n\');\n  let html = \'\';\n  for(const line of lines){\n    let matched = null;\n    for(const s of SECTIONS){ if(line.indexOf(s.m) !== -1){ matched = s; break; } }\n    if(matched){\n      html += \'<div class="sechead">\'+decorate(line)+\'</div>\'+\n              \'<div class="seccap">\'+matched.c+\'</div>\';\n      continue;\n    }\n    html += decorate(line) + \'\\n\';\n  }\n  document.getElementById(\'outtext\').innerHTML = html;\n  document.getElementById(\'output\').classList.add(\'show\');\n  document.getElementById(\'output\').scrollIntoView({behavior:\'smooth\',block:\'start\'});\n}\nfunction showTakeaways(){\n  const t = document.getElementById(\'takeaways\');\n  t.style.display=\'block\'; t.classList.add(\'show\');\n  t.scrollIntoView({behavior:\'smooth\',block:\'start\'});\n}\ndocument.getElementById(\'run\').addEventListener(\'click\',function(){\n  const btn=this, spin=document.getElementById(\'spin\');\n  btn.disabled=true; spin.classList.add(\'show\');\n  fetch(\'/api/run\').then(r=>r.json()).then(j=>{\n    spin.classList.remove(\'show\'); btn.disabled=false;\n    renderOut(j.output);\n    if(typeof loadDecisionTable===\'function\') loadDecisionTable();\n    showTakeaways();\n  }).catch(e=>{spin.classList.remove(\'show\');btn.disabled=false;alert(\'Run failed: \'+e);});\n});\n\nfunction collectCustom(){\n  return {category:document.getElementById(\'u_cat\').value};\n}\n\nfunction wireCustom(){\n  const b=document.getElementById(\'customRun\');\n  if(!b) return;\n  b.addEventListener(\'click\',function(){\n    const spin=document.getElementById(\'cspin\');\n    b.disabled=true; spin.classList.add(\'show\');\n    fetch(\'/api/custom\',{method:\'POST\',headers:{\'Content-Type\':\'application/json\'},\n      body:JSON.stringify(collectCustom())})\n    .then(r=>r.json()).then(j=>{\n      spin.classList.remove(\'show\'); b.disabled=false;\n      if(j.error){alert(j.error);return;}\n      renderOut(j.output); showTakeaways();\n    }).catch(e=>{spin.classList.remove(\'show\');b.disabled=false;alert(\'Run failed: \'+e);});\n  });\n}\nwireCustom();\n</script>\n</body>\n</html>\n'

class Handler(http.server.BaseHTTPRequestHandler):
    server_version = "WorkshopUI/1.0"

    def _send(self, body, ctype="text/html; charset=utf-8"):
        data = body.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _json(self, obj):
        self._send(json.dumps(obj), "application/json; charset=utf-8")

    def _read_json(self):
        try:
            length = int(self.headers.get("Content-Length", 0))
        except (TypeError, ValueError):
            length = 0
        raw = self.rfile.read(length) if length else b"{}"
        return json.loads(raw.decode("utf-8") or "{}")

    def _serve_asset(self, path):
        safe = (HERE / path.lstrip("/")).resolve()
        try:
            safe.relative_to(HERE / "assets")
        except ValueError:
            return self.send_error(403, "forbidden")
        if not safe.is_file():
            return self.send_error(404, "not found")
        ctype, _ = mimetypes.guess_type(str(safe))
        data = safe.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", ctype or "application/octet-stream")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "public, max-age=3600")
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        path = urllib.parse.urlsplit(self.path).path
        if path in ("/", "/index.html"):
            self._send(PAGE)
        elif path == "/api/run":
            self._json({"output": _capture_canned()})
        elif path.startswith("/assets/"):
            self._serve_asset(path)
        else:
            self.send_error(404, "not found")

    def do_POST(self):
        path = urllib.parse.urlsplit(self.path).path
        if path == "/api/custom":
            params = self._read_json()
            self._json({"output": _capture_fn(run_custom, params)})
        else:
            self.send_error(404, "not found")

    def log_message(self, fmt, *args):
        sys.stderr.write("ui: " + (fmt % args) + "\n")


def main():
    server = http.server.ThreadingHTTPServer((HOST, PORT), Handler)
    print("GuestFirst AI demo UI -> http://localhost:8008")
    print("Press Ctrl-C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nstopped.")


if __name__ == "__main__":
    main()
