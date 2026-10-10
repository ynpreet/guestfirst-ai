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

# _capture_custom: personalized handlers may return a dict carrying a follow-up decision.
def _capture_custom(fn, params):
    try:
        res = fn(params)
    except Exception as exc:  # never crash the page on a bad input
        return {"output": "[web-ui] The personalized run hit an error and stopped safely.", "decision": None}
    if isinstance(res, dict):
        res.setdefault("decision", None)
        return res
    return {"output": res, "decision": None}

# ---- personalized run: input handling lives in app.py; demo.py untouched ----

_GF_LABELS = {
    "long_wait": "long wait times",
    "missing_items": "missing items",
    "incorrect_orders": "incorrect orders",
    "delivery_delay": "delivery delays",
}

_GF_KEYWORDS = [
    ("incorrect_orders", ("wrong", "instead of", "not what i ordered", "mistake", "messed up")),
    ("missing_items", ("missing", "forgot", "didn't get", "did not get", "left out")),
    ("delivery_delay", ("delivery", "delivered", "driver", "arrived cold")),
    ("long_wait", ("wait", "waiting", "late", "slow", "minutes", "took", "forever", "long", "ready", "cold")),
]

_GF_WHY_NEXT = {
    "long_wait": "a wait complaint is usually a capacity problem, so I check volume and station queues before anything else",
    "missing_items": "a missing item is usually a bagging / expedite error, so I verify pickup records and the order contents first",
    "incorrect_orders": "a wrong order usually starts at order-taking or the line, so I pull the original order record first",
    "delivery_delay": "a delivery complaint spans kitchen and driver, so I check promised time against kitchen and pickup records",
}

# Recovery playbooks per category: (plan A, plan B). Deterministic.
_GF_PLANS = {
    "long_wait": [("Replace the meal + $5 coupon + personal apology SMS", "replacement + $5 coupon"),
                  ("Priority re-fire + full refund + $10 coupon", "refund + $10 coupon")],
    "missing_items": [("Replace the missing item + $5 coupon", "replacement + $5 coupon"),
                      ("Replace the item + 20% off the next visit", "replacement + 20% next-visit coupon")],
    "incorrect_orders": [("Remake the correct order + $5 coupon", "remake + $5 coupon"),
                         ("Remake + refund the wrong item", "remake + item refund")],
    "delivery_delay": [("Priority redelivery + $5 coupon", "redelivery + $5 coupon"),
                       ("Refund the delivery fee + $10 coupon", "delivery-fee refund + $10 coupon")],
}

def _gf_categorize(text):
    t = text.lower()
    for cat, kws in _GF_KEYWORDS:
        hits = [kw for kw in kws if kw in t]
        if hits:
            return cat, hits, False
    return "long_wait", [], True

def _gf_start(params):
    text = (params.get("text") or "").strip()
    if not text:
        return {"output": "Type your complaint above first -- the agent needs something to investigate.",
                "decision": None}
    text = text[:500]
    cat, hits, defaulted = _gf_categorize(text)
    orders, complaints, pickup_records = DEMO.build_world()
    mine = [c for c in complaints if c["category"] == cat]
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        print("=" * 70)
        print("YOUR COMPLAINT -- interactive recovery loop")
        print("=" * 70)
        print('You (the customer) said: "%s"' % text)
        print()
        if defaulted:
            print("[ORCHESTRATOR] Thinking: I could not match this to a strong keyword, so I default to the largest complaint cluster -- long wait times. (Honest fallback, flagged.)")
        else:
            print("[ORCHESTRATOR] Thinking: I categorized this as '%s' because of the word(s) %s." % (_GF_LABELS[cat], ", ".join(repr(h) for h in hits)))
        print("[ORCHESTRATOR] Thinking: %s." % _GF_WHY_NEXT[cat])
        print()
        counts = DEMO.t_categorize_complaints(complaints)
        print("Full-day complaint mix:", counts)
        conc = DEMO.t_complaint_concentration(complaints, cat)
        peak = {b: conc.get(b, 0) for b in DEMO.BUCKETS if conc.get(b, 0)}
        print("Concentration of '%s' by bucket:" % cat, peak)
        today, base, peak_today, peak_base = DEMO.t_compare_volume()
        print("Volume context: %d orders today vs %d baseline; peak %s -> %s." % (today, base, peak_base, peak_today))
        c0 = mine[0] if mine else None
        if c0:
            print()
            print("[ORCHESTRATOR] Thinking: zooming into one matching complaint so the recovery is personal, not generic: %s." % c0["id"])
            print('Complaint: %s -- "%s" (order %s)' % (c0["id"], c0["text"], c0["order_id"]))
            print("Order lookup:", DEMO.t_lookup_order(orders, c0["order_id"]))
            print("Pickup verification:", DEMO.t_verify_pickup(pickup_records, c0["order_id"]))
        plan_desc, plan_action = _GF_PLANS[cat][0]
        print()
        print("[ORCHESTRATOR] Thinking: a real recovery has four parts -- sorry, act, recover, follow up. Checking the proposed plan against policy before I bring it to you.")
        print("Policy check:", DEMO.t_check_recovery_policy(plan_action))
        print()
        print("=" * 70)
        print("PROPOSED RECOVERY PLAN -- needs YOUR approval (you are the manager):")
        print("  1. Sorry    -- personal apology message to the guest (drafted on approval)")
        print("  2. Act      -- %s" % plan_desc)
        print("  3. Recover  -- 48h follow-up scheduled to confirm the guest is happy")
        print("  4. Share    -- the root cause is logged for the kitchen team")
        print("=" * 70)
    decision = {"category": cat, "plan_idx": 0,
                "complaint_id": c0["id"] if c0 else None,
                "order_id": c0["order_id"] if c0 else None,
                "text": text, "plan_desc": plan_desc, "round": 1}
    return {"output": out.getvalue(), "decision": decision}

def _gf_decide(params):
    decision = (params.get("decision") or "").strip().lower()
    cat = params.get("category") or "long_wait"
    if cat not in _GF_LABELS:
        cat = "long_wait"
    try:
        plan_idx = int(params.get("plan_idx") or 0)
    except (TypeError, ValueError):
        plan_idx = 0
    plan_idx = max(0, min(plan_idx, 1))
    complaint_id = params.get("complaint_id")
    order_id = params.get("order_id")
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        if decision == "approve":
            plan_desc, plan_action = _GF_PLANS[cat][plan_idx]
            print('[ORCHESTRATOR] You approved: "%s". Executing -- the agent never acts on a recovery without a human tap.' % plan_desc)
            print("Manager approval:", DEMO.t_request_approval(plan_action, "you (store manager)"))
            orders, complaints, _ = DEMO.build_world()
            c0 = next((c for c in complaints if c["id"] == complaint_id), None)
            customer = "Guest"
            if c0:
                o = DEMO.t_lookup_order(orders, c0["order_id"])
                if o:
                    customer = o.get("customer", "Guest")
            msg = DEMO.t_draft_recovery_response(customer, order_id or "n/a", "12:25 PM", "12:40 PM", "$5")
            print()
            print("[ORCHESTRATOR] Personalizing the message for a '%s' complaint -- like the Chick-fil-A manager's call, it is personal, not a form letter:" % _GF_LABELS[cat])
            print('"%s"' % msg)
            print()
            print("Follow-up tracking: %s marked for 48h follow-up -- the agent will check back that the guest is happy." % (complaint_id or "the complaint"))
            print()
            print("[ORCHESTRATOR] Closed loop: investigate -> propose -> YOU approved -> message sent -> follow-up scheduled. That is the whole demo in one complaint.")
            return {"output": out.getvalue(), "decision": None}
        if plan_idx >= 1:
            print("[ORCHESTRATOR] You rejected both options. The agent will not improvise outside policy -- escalating to you, the human, for a personal visit. (Highest-touch recovery there is.)")
            print("Escalation logged: complaint flagged for in-person manager outreach.")
            return {"output": out.getvalue(), "decision": None}
        plan_desc, plan_action = _GF_PLANS[cat][1]
        verb = "adjusted" if decision == "adjust" else "rejected"
        print("[ORCHESTRATOR] You %s the first plan. Fair enough -- here is the next-best alternative allowed by policy:" % verb)
        print("Policy check:", DEMO.t_check_recovery_policy(plan_action))
        print()
        print("=" * 70)
        print("ALTERNATIVE RECOVERY PLAN -- needs YOUR approval:")
        print("  1. Sorry    -- personal apology message to the guest")
        print("  2. Act      -- %s" % plan_desc)
        print("  3. Recover  -- 48h follow-up scheduled")
        print("  4. Share    -- root cause logged for the kitchen team")
        print("=" * 70)
        decision2 = {"category": cat, "plan_idx": 1, "complaint_id": complaint_id,
                     "order_id": order_id, "text": (params.get("text") or "")[:500],
                     "plan_desc": plan_desc, "round": 2, "final": True}
        return {"output": out.getvalue(), "decision": decision2}

def run_custom(params):
    step = (params.get("step") or "start").strip().lower()
    if step == "decide":
        return _gf_decide(params)
    return _gf_start(params)

PAGE = '<!DOCTYPE html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n<meta name="viewport" content="width=device-width, initial-scale=1">\n<title>GuestFirst AI &mdash; Live Demo</title>\n<style>\n:root{\n  --bg:#0b1220; --bg2:#0e1626; --panel:#131e33; --panel2:#182742;\n  --ink:#eaf0f9; --muted:#9db0c9; --faint:#6b7f99;\n  --teal:#2dd4bf; --teal-dim:rgba(45,212,191,.12);\n  --accent:#5aa9ff; --warn:#fbbf24; --danger:#f87171; --ok:#34d399;\n  --line:#233451; --radius:14px;\n}\n*{box-sizing:border-box}\nbody{margin:0;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;\n  background:var(--bg);color:var(--ink);line-height:1.6}\nheader{background:linear-gradient(135deg,#0a2540 0%,#0e3a5c 60%,#0b4f4a 100%);\n  padding:42px 32px 34px;border-bottom:1px solid var(--line)}\n.wrap{max-width:1060px;margin:0 auto}\nheader h1{margin:0 0 8px;font-size:30px;letter-spacing:-.01em}\nheader .sub{margin:0;color:#c8d6ea;font-size:16px;max-width:800px}\n.badge{display:inline-block;margin-top:14px;font-size:11.5px;letter-spacing:.1em;\n  text-transform:uppercase;color:#06281f;background:var(--teal);\n  padding:5px 14px;border-radius:999px;font-weight:800}\nmain{padding:8px 32px 48px}\nsection.card{background:var(--panel);border:1px solid var(--line);\n  border-radius:var(--radius);padding:26px 28px;margin:26px 0}\nsection.card h2{margin:0 0 12px;font-size:18px;color:var(--teal)}\nsection.card h2 .n{display:inline-block;width:28px;height:28px;border-radius:50%;\n  background:var(--teal-dim);border:1px solid var(--teal);color:var(--teal);\n  text-align:center;line-height:26px;font-size:14px;margin-right:10px}\nsection.card p{margin:0 0 12px;color:#d5e0f1;font-size:15.5px}\nsection.card p:last-child{margin-bottom:0}\n.watch{list-style:none;margin:6px 0 0;padding:0}\n.watch li{position:relative;padding:8px 0 8px 30px;color:#d5e0f1;font-size:15px;\n  border-bottom:1px dashed var(--line)}\n.watch li:last-child{border-bottom:0}\n.watch li::before{content:"\\25b8";position:absolute;left:8px;color:var(--teal);font-weight:700}\nlabel.f{display:block;margin:14px 0 6px;font-size:13px;font-weight:700;\n  letter-spacing:.04em;text-transform:uppercase;color:var(--muted)}\ninput[type=text],input[type=number],select,textarea{\n  width:100%;background:var(--bg2);border:1px solid var(--line);color:var(--ink);\n  border-radius:10px;padding:11px 14px;font-size:15px;font-family:inherit}\ntextarea{min-height:76px;resize:vertical}\ninput:focus,select:focus,textarea:focus{outline:none;border-color:var(--teal)}\n.row2{display:grid;grid-template-columns:1fr 1fr;gap:14px}\n@media(max-width:700px){.row2{grid-template-columns:1fr}}\n.btnrow{display:flex;gap:14px;align-items:center;margin-top:20px;flex-wrap:wrap}\nbutton.run{background:linear-gradient(135deg,#14b8a6,#0d9488);border:0;\n  color:#04211c;font-weight:800;font-size:17px;padding:15px 34px;\n  border-radius:12px;cursor:pointer;box-shadow:0 6px 22px rgba(45,212,191,.25)}\nbutton.run:hover{filter:brightness(1.08)}\nbutton.run:disabled{opacity:.45;cursor:default;box-shadow:none}\nbutton.ghost{background:transparent;border:1px solid var(--teal);color:var(--teal);\n  font-weight:700;font-size:15px;padding:13px 26px;border-radius:12px;cursor:pointer}\nbutton.ghost:hover{background:var(--teal-dim)}\nbutton.ghost:disabled{opacity:.45;cursor:default}\n.hint{color:var(--muted);font-size:13.5px}\n.spinner{display:none;align-items:center;gap:10px;color:var(--muted);font-size:14px;margin-top:14px}\n.spinner.show{display:flex}\n.dot{width:12px;height:12px;border-radius:50%;background:var(--teal);\n  animation:pulse 1s infinite ease-in-out}\n@keyframes pulse{0%,100%{transform:scale(.6);opacity:.5}50%{transform:scale(1.2);opacity:1}}\n#output{display:none;margin-top:6px}\n#output.show{display:block}\n.out{background:#0a0f1c;border:1px solid var(--line);border-radius:12px;\n  padding:20px 22px;font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;\n  font-size:13px;line-height:1.6;white-space:pre-wrap;word-wrap:break-word;\n  max-height:640px;overflow:auto;color:#c9d6ea}\n.sechead{color:var(--accent);font-weight:800;margin:18px 0 2px;font-size:13.5px}\n.sechead:first-child{margin-top:0}\n.seccap{background:var(--teal-dim);border-left:3px solid var(--teal);\n  padding:8px 12px;margin:4px 0 12px;border-radius:0 8px 8px 0;\n  font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;\n  font-size:13.5px;color:#bfe9e2}\n.tok-orch{color:var(--accent);font-weight:700}\n.tok-tool{color:var(--ok);font-weight:700}\n.tok-guard{color:var(--warn);font-weight:700}\n.tok-mem{color:#c084fc;font-weight:700}\n#takeaways{display:none}\n#takeaways.show{display:block}\n.take{background:rgba(52,211,153,.07);border:1px solid rgba(52,211,153,.4);\n  border-radius:var(--radius);padding:22px 26px;margin:26px 0}\n.take h2{color:var(--ok);margin:0 0 10px;font-size:18px}\n.take ul{margin:0;padding-left:20px}\n.take li{margin:8px 0;color:#d5e0f1;font-size:15px}\ntable.dec{width:100%;border-collapse:collapse;margin-top:12px;font-size:14px}\ntable.dec th{background:var(--panel2);color:var(--teal);text-align:left;\n  padding:10px 12px;font-size:12px;letter-spacing:.06em;text-transform:uppercase;\n  border-bottom:1px solid var(--line)}\ntable.dec td{padding:10px 12px;border-bottom:1px solid var(--line);vertical-align:top}\n.pill{display:inline-block;padding:3px 12px;border-radius:999px;font-weight:800;font-size:12px}\n.pill.v{background:var(--ok);color:#04281c}\n.pill.s{background:var(--faint);color:#0b1220}\nfooter{padding:26px 32px 40px;color:var(--faint);font-size:13.5px;text-align:center}\nfooter a{color:var(--teal);text-decoration:none}\nfooter a:hover{text-decoration:underline}\ndetails.raw{margin-top:14px}\ndetails.raw summary{cursor:pointer;color:var(--muted);font-size:13.5px}\n\n/* --- guestfirst revamp: why-section + sidebar layout --- */\n.gf-layout{display:grid;grid-template-columns:minmax(0,1fr) 340px;gap:26px;align-items:start}\n.gf-main{min-width:0}\n.gf-sidebar{position:sticky;top:20px;min-width:0}\n@media(max-width:960px){.gf-layout{grid-template-columns:1fr}.gf-sidebar{position:static}}\n.side-card{background:var(--panel);border:1px solid var(--line);border-radius:var(--radius);padding:20px;margin-bottom:20px}\n.side-card h3{margin:0 0 10px;font-size:15px;color:var(--teal)}\n.side-vid{margin-bottom:18px}\n.side-vid:last-child{margin-bottom:0}\n.side-vid iframe{width:100%;aspect-ratio:16/9;border:0;border-radius:10px;display:block;background:#000}\n.side-vid p{font-size:13px;color:var(--muted);margin:8px 0 0;line-height:1.5}\n.why-grid{display:grid;grid-template-columns:repeat(2,1fr);gap:14px;margin:16px 0}\n@media(max-width:700px){.why-grid{grid-template-columns:1fr}}\n.why-grid figure{margin:0}\n.why-grid img{width:100%;aspect-ratio:16/10;object-fit:cover;border-radius:10px;border:1px solid var(--line);display:block;background:#0a0f1c}\n.why-grid figcaption{font-size:12.5px;color:var(--muted);margin-top:6px;line-height:1.5}\n.chips{display:flex;flex-wrap:wrap;gap:8px;margin:8px 0 4px}\n.chip{background:var(--panel2);border:1px solid var(--teal);color:var(--teal);font-size:13px;padding:7px 14px;border-radius:999px;cursor:pointer;font-family:inherit;line-height:1.4}\n.chip:hover{background:var(--teal-dim)}\n.research{background:rgba(90,169,255,.07);border:1px solid rgba(90,169,255,.45);border-radius:12px;padding:16px 18px;margin:16px 0}\n.research h4{margin:0 0 8px;font-size:13px;color:var(--accent);letter-spacing:.05em;text-transform:uppercase}\n.research p{margin:0 0 8px;font-size:14px;color:#d5e0f1;line-height:1.6}\n.research p:last-child{margin-bottom:0}\n.decpoint{background:rgba(251,191,36,.06);border:1px solid rgba(251,191,36,.5);border-radius:12px;padding:18px 20px;margin-top:16px}\n.decpoint h3{margin:0 0 8px;font-size:16px;color:var(--warn)}\n.decpoint p{margin:0 0 10px;font-size:14.5px;color:#d5e0f1}\n\n</style>\n</head>\n<body>\n<header><div class="wrap">\n  <h1>GuestFirst AI</h1>\n  <p class="sub">You are the manager on duty at TastePoint Downtown. Friday, 11:47 AM. The lunch rush is peaking — and your phone is buzzing with complaints.</p>\n</div></header>\n<main><div class="wrap gf-layout"><div class="gf-main">\n\n\n<section class="card" id="why">\n  <h2><span class="n">★</span>Why the recovery matters more than the mistake</h2>\n  <p>Every restaurant has a bad lunch rush. What separates the places guests come back to isn&rsquo;t perfection &mdash; it&rsquo;s what happens <b>after</b> something goes wrong. A guest whose complaint is handled well often ends up <b>more</b> loyal than one who never had a problem at all. Researchers call this the <b>service recovery paradox</b>: the recovery reveals your character under pressure, and character is what people remember.</p>\n  <p>An unhappy guest doesn&rsquo;t just leave quietly &mdash; they tell friends, family, and the internet. And winning a brand-new customer costs far more than keeping the one you already have. So every complaint is really a retention decision: recover well, or lose them for good.</p>\n  <div class="why-grid">\n    <figure><img src="/assets/img/lunch-rush.svg" alt="A packed restaurant dining room during the lunch rush" loading="lazy"><figcaption>Friday, 11:47 AM: the lunch rush at its peak &mdash; this is when complaints spike.</figcaption></figure>\n    <figure><img src="/assets/img/kitchen-line.svg" alt="Cooks working the line in a busy commercial kitchen" loading="lazy"><figcaption>The line under pressure: where most delays are born.</figcaption></figure>\n    <figure><img src="/assets/img/fryer-station.svg" alt="French fries cooking in a commercial fryer" loading="lazy"><figcaption>The fryer station &mdash; watch what happens when one goes offline mid-demo.</figcaption></figure>\n    <figure><img src="/assets/img/happy-diners.svg" alt="Happy diners enjoying a meal together at a restaurant" loading="lazy"><figcaption>The goal: guests who leave happy &mdash; and come back.</figcaption></figure>\n  </div>\n  <div class="research">\n    <h4>Grounded in research</h4>\n    <p>Customer-experience researchers who measured service components across major fast-food chains &mdash; Chipotle, Subway, KFC, Dairy Queen, Taco Bell, Chick-fil-A &mdash; found the strongest driver of overall satisfaction wasn&rsquo;t speed. It was <b>attentive, courteous service</b>.</p>\n    <p>And Chick-fil-A, famous for its &ldquo;my pleasure&rdquo; culture &mdash; where a manager once replaced a customer&rsquo;s order free and delivered it to her doorstep &mdash; consistently tops customer-experience rankings in the $300B limited-service industry. This isn&rsquo;t just a demo narrative: the human touch moves the satisfaction needle most. That&rsquo;s why GuestFirst treats every complaint as a relationship to repair, not a ticket to close.</p>\n  </div>\n  <p><b>The purpose of this demo:</b> it puts <b>you</b> in the manager&rsquo;s chair during a Friday lunch rush. The agent is your investigator &mdash; it finds <i>why</i> complaints are spiking, coordinates the fix, recovers the guests personally, and proves the fix worked before the next rush. And at the key moment, it stops and asks <b>you</b> &mdash; approve the recovery, or send it back.</p>\n</section>\n\n<section class="card" id="story">\n  <h2><span class="n">1</span>The story</h2>\n  <p>You are the manager on duty at TastePoint Downtown. Friday, 11:47 AM: the lunch rush is peaking and complaints are spiking. A dashboard would say “satisfaction declined 12%.” A chatbot would say “customers mention long wait times.” Neither tells <b>you</b> what to <b>do</b> — and you are the one on the hook.</p>\n<p>GuestFirst is the agent that does: it categorizes the complaints, chooses which operational data to inspect <i>from the pattern</i>, tests three root-cause hypotheses while keeping correlation and causation strictly separate, recovers the affected customers within policy, forecasts demand — and verifies the fix with a simulation. Then the twist: a fryer goes offline tomorrow, and the agent replans under the new constraint <i>before</i> lunch.</p>\n</section>\n\n<section class="card" id="watch">\n  <h2><span class="n">2</span>What to watch for</h2>\n  <ul class="watch">\n<li>Watch the agent pick its own investigation path from the complaint pattern — not a generic data dump.</li>\n<li>The correlation trap: naive grill-volume correlation says r = −0.43 (wrong sign!). Watch the agent test the <i>mechanism</i> instead.</li>\n<li>The twist: a fryer goes offline. The agent replans under the new constraint and simulates both plans.</li>\n<li>The scoreboard: agent vs. fixed-staffing baseline on identical simulated data.</li>\n  </ul>\n</section>\n\n\n\n<section class="card" id="tryown">\n  <h2><span class="n">✎</span>Try your own — you be the customer, then the manager</h2>\n  <p>Type <b>your</b> complaint in your own words, as if you are the unhappy customer. The agent will think out loud, categorize it, and investigate — then stop and ask <b>you</b> (now the manager) to approve the recovery.</p>\n  <label class="f">Not sure what to write? Try one of these:</label>\n  <div class="chips">\n    <button type="button" class="chip">My burger took 40 minutes</button>\n    <button type="button" class="chip">Fries were missing from my bag</button>\n    <button type="button" class="chip">I got the wrong sandwich</button>\n    <button type="button" class="chip">My delivery arrived cold and late</button>\n  </div>\n  <label class="f" for="u_text">Your complaint</label>\n  <textarea id="u_text" placeholder="e.g. I waited 25 minutes and my fries were cold"></textarea>\n  <div class="btnrow">\n    <button class="ghost" id="gfRun">Investigate my complaint</button>\n    <span class="hint">Same inputs → same output. Deterministic.</span>\n  </div>\n  <div class="spinner" id="cspin"><div class="dot"></div>Investigating…</div>\n  <div id="decbox" style="display:none"></div>\n</section>\n\n\n<section class="card" id="runbox">\n  <h2><span class="n">3</span>Run the demo</h2>\n  <p>Click below to run the full canned demonstration. It takes a few seconds.</p>\n  <div class="btnrow">\n    <button class="run" id="run">&#9654; Run live demo</button>\n  </div>\n  <div class="spinner" id="spin"><div class="dot"></div><span>The agent is investigating the complaints…</span></div>\n  <div id="output">\n    <div class="out" id="outtext"></div>\n    <details class="raw"><summary>Show raw terminal output</summary>\n      <div class="out" id="rawtext"></div>\n    </details>\n  </div>\n</section>\n\n<section class="card" id="takeaways" style="display:none">\n  <div class="take">\n    <h2>What just happened</h2>\n    <ul>\n<li>Correlation lied (r = −0.43); the mechanism told the truth: grill arrivals exceeded capacity for 45 straight minutes.</li>\n<li>Staffing was explicitly NOT blamed — it never varied, and a constant can\'t explain a change.</li>\n<li>The twist proved agency: new constraint in, revised plan out, both simulated before lunch.</li>\n<li>Recovery was closed-loop: every affected customer tracked to resolution, not just apologized to.</li>\n<li>Try your own: type a complaint in your own words in “Try your own” — the agent categorizes it and focuses the investigation on it.</li>\n    </ul>\n  </div>\n</section>\n\n</div>\n<aside class="gf-sidebar">\n  <div class="side-card">\n    <h3>Learn more</h3>\n    <p style="font-size:13.5px;color:var(--muted);margin:0 0 14px">Want to go deeper on service recovery? Start with these.</p>\n    <div class="side-vid">\n      <iframe src="https://www.youtube-nocookie.com/embed/Z3_EYa6V_k0" title="How great restaurants recover mistakes" loading="lazy" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" allowfullscreen></iframe>\n      <p>Restaurant-specific: what servers get wrong when mistakes happen &mdash; and the recovery moves that actually work. Guests forgive mistakes; they don&rsquo;t forgive indifference.</p>\n    </div>\n    <div class="side-vid">\n      <iframe src="https://www.youtube-nocookie.com/embed/xp0Io26H4i0" title="The service recovery paradox, explained" loading="lazy" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" allowfullscreen></iframe>\n      <p>The service recovery paradox explained: why a well-handled failure can leave customers <i>more</i> loyal than if nothing had gone wrong &mdash; and why most companies only do two-thirds of it.</p>\n    </div>\n    <div class="side-vid">\n      <iframe src="https://www.youtube-nocookie.com/embed/5kNZhz_KQ1Q" title="Service and hospitality at Chick-fil-A" loading="lazy" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" allowfullscreen></iframe>\n      <p>The real-world exemplar: how Chick-fil-A&rsquo;s service culture &mdash; &ldquo;my pleasure&rdquo; and all &mdash; keeps it at #1 on customer experience.</p>\n    </div>\n  </div>\n</aside>\n</div></main>\n<footer><div class="wrap">\n  <a href="https://github.com/ynpreet/guestfirst-ai" target="_blank" rel="noopener">View the project on GitHub</a>\n  &nbsp;&middot;&nbsp; All data in this demo is synthetic / fictional.\n</div></footer>\n\n<script>\nconst SECTIONS = [["STEP 1/6", "Categorize: what are customers actually complaining about?"], ["STEP 2/6", "Investigate: volume, timestamps, demand, staffing, inventory \\u2014 chosen from the pattern, not dumped generically."], ["STEP 3/6", "Root cause: three hypotheses tested, correlation separated from causation. The priority feature."], ["STEP 4/6", "Service recovery: one complaint handled end-to-end, within policy, with approval."], ["STEP 5/6", "Coordinate: demand forecast, kitchen check, the adjusted plan."], ["STEP 6/6", "Verify: simulation compares original vs. revised plan before the next rush."], ["EVALUATION", "Agent vs. baseline on identical data \\u2014 simulated outcomes, labeled as such."], ["WHY AN AGENT", "The closing argument: what a dashboard and a chatbot would have said instead."]];\nfunction esc(s){return s.replace(/&/g,\'&amp;\').replace(/</g,\'&lt;\').replace(/>/g,\'&gt;\');}\nfunction decorate(line){\n  let h = esc(line);\n  h = h.replace(/\\[ORCHESTRATOR\\]/g,\'<span class="tok-orch">[ORCHESTRATOR]</span>\');\n  h = h.replace(/\\[TOOL [^\\]]+\\]/g,function(m){return \'<span class="tok-tool">\'+m+\'</span>\';});\n  h = h.replace(/\\[MEMORY\\]/g,\'<span class="tok-mem">[MEMORY]</span>\');\n  h = h.replace(/GUARDRAIL/g,\'<span class="tok-guard">GUARDRAIL</span>\');\n  return h;\n}\nfunction renderOut(text){\n  document.getElementById(\'rawtext\').textContent = text;\n  const lines = text.split(\'\\n\');\n  let html = \'\';\n  for(const line of lines){\n    let matched = null;\n    for(const s of SECTIONS){ if(line.indexOf(s.m) !== -1){ matched = s; break; } }\n    if(matched){\n      html += \'<div class="sechead">\'+decorate(line)+\'</div>\'+\n              \'<div class="seccap">\'+matched.c+\'</div>\';\n      continue;\n    }\n    html += decorate(line) + \'\\n\';\n  }\n  document.getElementById(\'outtext\').innerHTML = html;\n  document.getElementById(\'output\').classList.add(\'show\');\n  document.getElementById(\'output\').scrollIntoView({behavior:\'smooth\',block:\'start\'});\n}\nfunction showTakeaways(){\n  const t = document.getElementById(\'takeaways\');\n  t.style.display=\'block\'; t.classList.add(\'show\');\n  t.scrollIntoView({behavior:\'smooth\',block:\'start\'});\n}\ndocument.getElementById(\'run\').addEventListener(\'click\',function(){\n  const btn=this, spin=document.getElementById(\'spin\');\n  btn.disabled=true; spin.classList.add(\'show\');\n  fetch(\'/api/run\').then(r=>r.json()).then(j=>{\n    spin.classList.remove(\'show\'); btn.disabled=false;\n    renderOut(j.output);\n    if(typeof loadDecisionTable===\'function\') loadDecisionTable();\n    showTakeaways();\n  }).catch(e=>{spin.classList.remove(\'show\');btn.disabled=false;alert(\'Run failed: \'+e);});\n});\n\nfunction collectCustom(){\n  return {step:"start", text:document.getElementById(\'u_text\').value};\n}\nfunction escH(s){return String(s).replace(/&/g,\'&amp;\').replace(/</g,\'&lt;\').replace(/>/g,\'&gt;\');}\nfunction renderDecision(d){\n  var box=document.getElementById(\'decbox\');\n  if(!d){box.innerHTML=\'\';box.style.display=\'none\';return;}\n  box.style.display=\'block\';\n  box.innerHTML=\n    \'<div class="decpoint"><h3>Manager decision required</h3>\'+\n    \'<p>The agent proposes: <b>\'+escH(d.plan_desc)+\'</b></p>\'+\n    \'<div class="btnrow">\'+\n    \'<button class="run" data-dec="approve">Approve</button>\'+\n    \'<button class="ghost" data-dec="adjust">Adjust</button>\'+\n    \'<button class="ghost" data-dec="reject">Reject</button>\'+\n    \'</div><p class="hint">The human-in-the-loop moment: the agent never executes a recovery without your tap.</p></div>\';\n  var btns=box.querySelectorAll(\'button\'),i;\n  for(i=0;i<btns.length;i++){\n    (function(btn){\n      btn.addEventListener(\'click\',function(){decideStep(btn.getAttribute(\'data-dec\'),d);});\n    })(btns[i]);\n  }\n  box.scrollIntoView({behavior:\'smooth\',block:\'center\'});\n}\nfunction decideStep(decision,d){\n  var spin=document.getElementById(\'cspin\');\n  spin.classList.add(\'show\');\n  fetch(\'/api/custom\',{method:\'POST\',headers:{\'Content-Type\':\'application/json\'},\n    body:JSON.stringify({step:\'decide\',decision:decision,category:d.category,plan_idx:d.plan_idx,\n      complaint_id:d.complaint_id,order_id:d.order_id,text:d.text})})\n  .then(function(r){return r.json();}).then(function(j){\n    spin.classList.remove(\'show\');\n    renderOut(j.output);renderDecision(j.decision);showTakeaways();\n  }).catch(function(e){spin.classList.remove(\'show\');alert(\'Run failed: \'+e);});\n}\n(function(){\n  var b=document.getElementById(\'gfRun\');\n  if(!b) return;\n  b.addEventListener(\'click\',function(){\n    var spin=document.getElementById(\'cspin\');\n    b.disabled=true;spin.classList.add(\'show\');renderDecision(null);\n    fetch(\'/api/custom\',{method:\'POST\',headers:{\'Content-Type\':\'application/json\'},\n      body:JSON.stringify(collectCustom())})\n    .then(function(r){return r.json();}).then(function(j){\n      spin.classList.remove(\'show\');b.disabled=false;\n      renderOut(j.output);renderDecision(j.decision);showTakeaways();\n    }).catch(function(e){spin.classList.remove(\'show\');b.disabled=false;alert(\'Run failed: \'+e);});\n  });\n  var chips=document.querySelectorAll(\'.chip\'),i;\n  for(i=0;i<chips.length;i++){\n    (function(ch){\n      ch.addEventListener(\'click\',function(){\n        var inp=document.getElementById(\'u_text\');\n        inp.value=ch.textContent.trim();\n        inp.scrollIntoView({behavior:\'smooth\',block:\'center\'});\n        inp.focus();\n      });\n    })(chips[i]);\n  }\n})();\n\nfunction wireCustom(){\n  const b=document.getElementById(\'customRun\');\n  if(!b) return;\n  b.addEventListener(\'click\',function(){\n    const spin=document.getElementById(\'cspin\');\n    b.disabled=true; spin.classList.add(\'show\');\n    fetch(\'/api/custom\',{method:\'POST\',headers:{\'Content-Type\':\'application/json\'},\n      body:JSON.stringify(collectCustom())})\n    .then(r=>r.json()).then(j=>{\n      spin.classList.remove(\'show\'); b.disabled=false;\n      if(j.error){alert(j.error);return;}\n      renderOut(j.output); showTakeaways();\n    }).catch(e=>{spin.classList.remove(\'show\');b.disabled=false;alert(\'Run failed: \'+e);});\n  });\n}\nwireCustom();\n</script>\n</body>\n</html>\n'

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
            self._json(_capture_custom(run_custom, params))
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
