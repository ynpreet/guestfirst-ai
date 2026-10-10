#!/usr/bin/env python3
"""
GuestFirst AI -- localhost web UI for the live demo.

Stdlib ONLY (http.server). No Flask, no Streamlit, no pip, no network.

    python3 app.py

Then open in Chrome: http://localhost:8008

  GET /         -> the single-page demo UI (inline CSS/JS, no external assets)
  GET /api/run  -> runs `demo.py` via subprocess, returns {"ok": true, "output": "..."}

demo.py is never modified -- it is run as a subprocess so the web UI and the
CLI demo can never drift apart.
"""

import errno
import http.server
import json
import os
import socketserver
import subprocess
import sys

HOST = "127.0.0.1"
PORT = 8008
HERE = os.path.dirname(os.path.abspath(__file__))

PAGE = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>GuestFirst AI — Live Demo</title>
<style>
  :root {
    --bg: #0d1117; --panel: #161b22; --panel2: #1c2330; --line: #2d3644;
    --ink: #e6edf3; --muted: #9aa7b8; --accent: #58a6ff; --teal: #3fb950;
    --amber: #d29922; --red: #f85149; --purple: #bc8cff;
  }
  * { box-sizing: border-box; }
  body { margin: 0; background: var(--bg); color: var(--ink);
         font: 15px/1.6 -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif; }
  .wrap { max-width: 980px; margin: 0 auto; padding: 32px 20px 64px; }
  header.hero { border: 1px solid var(--line); border-radius: 14px;
    background: linear-gradient(135deg, #16202e 0%, #10151f 100%);
    padding: 28px 30px; margin-bottom: 22px; }
  header.hero h1 { margin: 0 0 4px; font-size: 30px; letter-spacing: .2px; }
  header.hero h1 .ai { color: var(--accent); }
  header.hero p.sub { margin: 0; color: var(--muted); font-size: 15px; }
  .badge { display: inline-block; margin-top: 10px; font-size: 12px; letter-spacing: .08em;
    color: #0d1117; background: var(--amber); border-radius: 999px; padding: 3px 12px;
    font-weight: 700; }
  .card { background: var(--panel); border: 1px solid var(--line); border-radius: 12px;
    padding: 20px 22px; margin-bottom: 20px; }
  .card h2 { margin: 0 0 10px; font-size: 17px; letter-spacing: .04em; text-transform: uppercase;
    color: var(--muted); }
  .story p { margin: 0 0 10px; }
  .story blockquote { margin: 12px 0; padding: 12px 16px; border-left: 4px solid var(--accent);
    background: var(--panel2); border-radius: 0 8px 8px 0; font-style: italic; }
  #runBtn { display: inline-block; font-size: 17px; font-weight: 700; color: #fff;
    background: #1f6feb; border: 0; border-radius: 10px; padding: 13px 34px; cursor: pointer; }
  #runBtn:hover:not(:disabled) { background: #2f81f7; }
  #runBtn:disabled { opacity: .55; cursor: wait; }
  #status { color: var(--muted); margin-left: 14px; font-size: 14px; }
  .spinner { display: none; margin: 18px auto; width: 44px; height: 44px;
    border: 4px solid var(--line); border-top-color: var(--accent); border-radius: 50%;
    animation: spin 0.9s linear infinite; }
  .spinner.on { display: block; }
  @keyframes spin { to { transform: rotate(360deg); } }
  #plan { display: none; background: #0f2a1a; border: 1px solid #2ea043; border-radius: 10px;
    padding: 16px 20px; margin-bottom: 16px; }
  #plan h3 { margin: 0 0 8px; font-size: 14px; letter-spacing: .06em; text-transform: uppercase;
    color: var(--teal); }
  #plan ol { margin: 0; padding-left: 22px; color: var(--ink); }
  #plan li { margin: 3px 0; font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
    font-size: 13.5px; }
  #traceWrap { display: none; }
  #trace { background: #0a0d12; border: 1px solid var(--line); border-radius: 10px;
    padding: 16px 18px; max-height: 560px; overflow: auto;
    font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
    font-size: 13px; line-height: 1.65; white-space: pre-wrap; word-break: break-word; }
  .t-orch { color: var(--teal); font-weight: 600; }
  .t-tool { color: var(--amber); }
  .t-step { color: var(--accent); font-weight: 700; font-size: 14px; }
  .t-banner { color: #fff; font-weight: 700; }
  .t-twist { color: var(--red); font-weight: 700; }
  .t-gate { color: var(--purple); font-weight: 700; }
  #results { display: none; }
  .resgrid { display: grid; grid-template-columns: repeat(auto-fit, minmax(210px, 1fr));
    gap: 12px; margin-bottom: 14px; }
  .rescard { background: var(--panel2); border: 1px solid var(--line); border-radius: 10px;
    padding: 14px 16px; }
  .rescard .k { font-size: 12px; text-transform: uppercase; letter-spacing: .06em;
    color: var(--muted); margin-bottom: 6px; }
  .rescard .v { font-size: 16px; font-weight: 700; }
  .rescard .v .neg { color: var(--red); } .rescard .v .pos { color: var(--teal); }
  .rescard .d { font-size: 13px; color: var(--muted); margin-top: 4px; }
  table.eval { width: 100%; border-collapse: collapse; font-size: 13.5px; }
  table.eval th, table.eval td { text-align: left; padding: 7px 10px; border-bottom: 1px solid var(--line); }
  table.eval th { color: var(--muted); text-transform: uppercase; font-size: 12px; letter-spacing: .05em; }
  table.eval td.num { font-family: ui-monospace, Menlo, Consolas, monospace; text-align: right; }
  .err { color: var(--red); font-weight: 600; }
  footer { color: var(--muted); font-size: 13px; margin-top: 26px; }
  footer code { background: var(--panel2); padding: 1px 6px; border-radius: 6px; }
</style>
</head>
<body>
<div class="wrap">

  <header class="hero">
    <h1>GuestFirst <span class="ai">AI</span></h1>
    <p class="sub">An Agentic AI System for Personalized Restaurant Experiences
      &middot; Demo 8 of 8, Agentic AI Workshop &middot; fictional TastePoint</p>
    <span class="badge">FICTIONAL — all data SYNTHETIC, outcomes SIMULATED</span>
  </header>

  <section class="card story">
    <h2>The story</h2>
    <p>It&rsquo;s Friday lunch at TastePoint Downtown. An unusual spike of complaints
       hits the inbox, and the manager asks the only question that matters:</p>
    <blockquote>&ldquo;Why are customers complaining about long wait times today,
       and what should we do?&rdquo;</blockquote>
    <p>A dashboard would answer <em>&ldquo;Satisfaction declined 12%.&rdquo;</em> A chatbot
       would answer <em>&ldquo;Customers mention long wait times.&rdquo;</em> Neither tells the
       manager what to <strong>do</strong>.</p>
    <p>GuestFirst AI is an <strong>agentic</strong> system: one orchestrator plans the
       investigation, calls tools to gather evidence, and works the full loop —
       categorize, investigate, root-cause (correlation &ne; causation), recover,
       coordinate, and <strong>verify by simulation</strong>.</p>
  </section>

  <section class="card">
    <h2>Live demo</h2>
    <button id="runBtn" onclick="runDemo()">&#9654; Run live demo</button>
    <span id="status">Runs the actual <code>demo.py</code> on this machine — offline, no API keys.</span>
    <div class="spinner" id="spinner" aria-label="running"></div>
    <div id="error" class="err"></div>
  </section>

  <section class="card" id="planCard" style="display:none">
    <h2>Agent trace — plan</h2>
    <div id="plan"><h3>&#9679; Orchestrator plan</h3><ol id="planList"></ol></div>
  </section>

  <section class="card" id="traceWrap">
    <h2>Agent trace — steps &amp; tool calls</h2>
    <div id="trace"></div>
  </section>

  <section class="card" id="results">
    <h2>Key results</h2>
    <div class="resgrid" id="resgrid"></div>
    <div id="evalTable"></div>
  </section>

  <footer>
    Tip: the same demo runs in the terminal with <code>python3 demo.py</code> —
    output is byte-identical on every run. See <code>TEST-LOG.md</code>.
  </footer>

</div>
<script>
"use strict";
function esc(s){ return s.replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;"); }

function renderPlan(text){
  var lines = text.split("\n"), plan = [], inPlan = false;
  for (var i = 0; i < lines.length; i++){
    var l = lines[i];
    if (l.indexOf("plan (capabilities in brackets):") !== -1){ inPlan = true; continue; }
    if (inPlan){
      if (l.trim() === "") break;
      plan.push(l.trim());
    }
  }
  var list = document.getElementById("planList");
  list.innerHTML = "";
  plan.forEach(function(p){
    var li = document.createElement("li"); li.textContent = p; list.appendChild(li);
  });
  document.getElementById("planCard").style.display = plan.length ? "" : "none";
}

function lineClass(l){
  if (l.indexOf("!!! TWIST") !== -1) return "t-twist";
  if (l.indexOf(">>> STEP") === 0) return "t-step";
  if (l.indexOf(">>> APPROVAL GATE") !== -1) return "t-gate";
  if (l.indexOf("[orchestrator]") !== -1) return "t-orch";
  if (l.indexOf("[tool]") !== -1) return "t-tool";
  if (/^=+$/.test(l.trim()) && l.length > 20) return "t-banner";
  return "";
}

function renderTrace(text){
  var div = document.getElementById("trace");
  div.innerHTML = "";
  var frag = document.createDocumentFragment();
  text.split("\n").forEach(function(l){
    var span = document.createElement("span");
    var cls = lineClass(l);
    if (cls) span.className = cls;
    span.textContent = l + "\n";
    frag.appendChild(span);
  });
  div.appendChild(frag);
  document.getElementById("traceWrap").style.display = "";
}

function first(re, text){ var m = re.exec(text); return m ? m[1] : null; }

function renderResults(text){
  var cards = [];
  var nComp = first(/categorize_complaints\(window="[^"]*", n=(\d+)/, text);
  var nLong = first(/^\s*-> long_wait: (\d+)$/m, text);
  if (nComp) cards.push({k:"Complaints triaged", v: nComp + " complaints",
    d: (nLong || "?") + " long waits, clustered in one window"});
  var rs = [], re = /Pearson r = (-?[\d.]+)/g, m;
  while ((m = re.exec(text))) rs.push(m[1]);
  if (rs.length >= 2) cards.push({k:"Correlation sign-flip", v: "r = " + rs[0] + " → r = +" + rs[1],
    d: "naive correlation has the wrong sign; a 30-min lag flips it"});
  var im = /grill avg wait: ([\d.]+) -> ([\d.]+) min \(-(\d+)%\)/.exec(text);
  if (im) cards.push({k:"Recommended fix", v: im[1] + " → " + im[2] + " min (−" + im[3] + "%)",
    d: "move 1 staff assemble → grill; sized by simulation, staged behind approval"});
  var blocked = /BLOCKED by policy guardrail/.test(text);
  if (/complaint marked RESOLVED/.test(text)) cards.push({k:"Service recovery",
    v: "complaint resolved end-to-end" + (blocked ? "; $20 refund blocked" : ""),
    d: "lookup → verify → policy check → draft → approve → record → verify"});
  var atRisk = first(/(\d+) fry orders needing outreach/, text);
  if (atRisk) cards.push({k:"Fryer-outage replan", v: "waits hold at ~5 min",
    d: "cost made explicit before lunch: " + atRisk + " fry orders need substitution outreach"});
  var gates = (text.match(/APPROVAL GATE/g) || []).length;
  if (gates) cards.push({k:"Approval gates", v: gates + " gates in the trace",
    d: "nothing staffing- or customer-facing executes without a (simulated) human tap"});

  var grid = document.getElementById("resgrid");
  grid.innerHTML = "";
  cards.forEach(function(c){
    var d = document.createElement("div"); d.className = "rescard";
    d.innerHTML = '<div class="k">' + esc(c.k) + '</div><div class="v">' + esc(c.v) +
                  '</div><div class="d">' + esc(c.d) + '</div>';
    grid.appendChild(d);
  });

  // Evaluation table: agent vs baseline, 7 simulated metrics.
  var evalIdx = text.indexOf("EVALUATION --");
  var rows = [];
  if (evalIdx !== -1){
    var evalText = text.slice(evalIdx);
    var lines = evalText.split("\n");
    for (var i = 0; i < lines.length; i++){
      var lm = /^  ([a-z][a-z /%]*\([^)]*\))\s+([\d.]+)\s+([\d.]+)$/.exec(lines[i]);
      if (lm && lm[1].indexOf("SIMULATED") === -1) rows.push([lm[1], lm[2], lm[3]]);
    }
  }
  var et = document.getElementById("evalTable");
  if (rows.length){
    var h = '<h2 style="margin-top:18px">Agent vs baseline (SIMULATED)</h2>' +
            '<table class="eval"><tr><th>Metric</th><th style="text-align:right">Baseline</th>' +
            '<th style="text-align:right">GuestFirst</th></tr>';
    rows.forEach(function(r){
      h += '<tr><td>' + esc(r[0]) + '</td><td class="num">' + esc(r[1]) +
           '</td><td class="num">' + esc(r[2]) + '</td></tr>';
    });
    et.innerHTML = h + '</table>';
  }
  document.getElementById("results").style.display = "";
}

async function runDemo(){
  var btn = document.getElementById("runBtn"), st = document.getElementById("status"),
      sp = document.getElementById("spinner"), err = document.getElementById("error");
  btn.disabled = true; err.textContent = "";
  document.getElementById("traceWrap").style.display = "none";
  document.getElementById("results").style.display = "none";
  document.getElementById("planCard").style.display = "none";
  sp.classList.add("on");
  st.textContent = "Running demo.py… (offline, ~1 second)";
  try {
    var res = await fetch("/api/run");
    if (!res.ok) throw new Error("server returned HTTP " + res.status);
    var data = await res.json();
    if (!data.ok) throw new Error(data.error || "demo failed");
    renderPlan(data.output);
    renderTrace(data.output);
    renderResults(data.output);
    st.textContent = "Done — trace rendered from live demo.py output (" +
                     data.output.length + " chars).";
  } catch (e){
    err.textContent = "Demo failed: " + e.message;
    st.textContent = "";
  } finally {
    sp.classList.remove("on");
    btn.disabled = false;
  }
}
</script>
</body>
</html>
"""

DEMO_TIMEOUT = 30  # seconds; demo.py itself takes <1s


class Handler(http.server.BaseHTTPRequestHandler):
    server_version = "GuestFirstUI/1.0"

    def _send(self, code, body, ctype):
        data = body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype + "; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        path = self.path.split("?", 1)[0]
        if path == "/":
            self._send(200, PAGE, "text/html")
        elif path == "/api/run":
            self._handle_run()
        elif path == "/favicon.ico":
            self.send_response(204)
            self.end_headers()
        else:
            self._send(404, "not found", "text/plain")

    def _handle_run(self):
        try:
            proc = subprocess.run(
                [sys.executable, "demo.py"],
                cwd=HERE,
                capture_output=True,
                text=True,
                timeout=DEMO_TIMEOUT,
            )
        except subprocess.TimeoutExpired:
            payload = {"ok": False,
                       "error": "demo.py timed out after %ds" % DEMO_TIMEOUT}
            self._send(500, json.dumps(payload), "application/json")
            return
        except OSError as e:
            payload = {"ok": False, "error": "could not start demo.py: %s" % e}
            self._send(500, json.dumps(payload), "application/json")
            return
        if proc.returncode != 0:
            payload = {"ok": False,
                       "error": "demo.py exited %d: %s"
                       % (proc.returncode, proc.stderr[-500:])}
            self._send(500, json.dumps(payload), "application/json")
            return
        payload = {"ok": True, "output": proc.stdout}
        self._send(200, json.dumps(payload), "application/json")

    def log_message(self, fmt, *args):  # quieter request logging
        sys.stderr.write("guestfirst-ui: %s\n" % (fmt % args))


def main():
    # SO_REUSEADDR so a restart (e.g. between test rounds) can rebind the
    # port immediately instead of tripping on TIME_WAIT sockets.
    socketserver.ThreadingTCPServer.allow_reuse_address = True
    # The constructor binds the port; OSError (EADDRINUSE) surfaces here and
    # is turned into a friendly message by the __main__ guard below.
    server = socketserver.ThreadingTCPServer((HOST, PORT), Handler)
    print("=" * 60)
    print("  GuestFirst AI demo server running")
    print("  Open in Chrome: http://localhost:%d" % PORT)
    print("=" * 60, flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nguestfirst-ui: stopped.")


if __name__ == "__main__":
    try:
        main()
    except OSError as e:
        if e.errno in (errno.EADDRINUSE, 98, 48):
            sys.stderr.write(
                "\nERROR: port %d is already in use on %s.\n"
                "Another copy of app.py (or something else) is already holding it.\n"
                "Stop it first, then run:  python3 app.py\n\n" % (PORT, HOST))
            sys.exit(1)
        raise
