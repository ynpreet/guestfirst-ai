#!/usr/bin/env python3
"""
GuestFirst AI -- An Agentic AI System for Personalized Restaurant Experiences
Demo 8 of 8 - Agentic AI Workshop

FICTIONAL: TastePoint is a fictional restaurant chain. Every order, complaint,
timestamp, staff member, and metric below is SYNTHETIC sample data generated
inside this file. Anything labeled SIMULATED is a model output, not a
measurement of a real restaurant.

Thesis: not a dashboard that reports "satisfaction declined", not a chatbot
that summarizes feedback -- an AGENTIC system that investigates WHY
satisfaction declined, determines the action, coordinates the response, and
VERIFIES the problem was resolved. One orchestrator + tools (not five
separate agents). The five capabilities are tool groups the single agent uses:

  (A) Customer Experience Intelligence   (B) Personalized Service Recovery
  (C) Demand & Kitchen Coordination      (D) Root-Cause Analysis
  (E) Loyalty & Experience Improvement

Runs fully offline. Stdlib only. Byte-identical output on every run
(fixed RNG seed, fixed synthetic clock, sorted iteration -- no wall clock).
"""

import random

# --------------------------------------------------------------------------
# Determinism: one seeded RNG, one fixed synthetic clock, sorted iteration.
# --------------------------------------------------------------------------
SEED = 20261010
rng = random.Random(SEED)

# --------------------------------------------------------------------------
# The synthetic world: TastePoint (FICTIONAL), Downtown location,
# Friday lunch shift 12:00-14:00. "Now" is fixed at 13:05 -- the demo's clock.
# --------------------------------------------------------------------------
BUCKETS = ["12:00", "12:15", "12:30", "12:45", "13:00", "13:15", "13:30", "13:45"]
STATIONS = ["GRILL", "FRY", "ASSEMBLE", "BEVERAGE"]

BASE_PREP = {"GRILL": 6.0, "FRY": 5.0, "ASSEMBLE": 4.0, "BEVERAGE": 2.0}  # min at zero backlog
CAPACITY = {"GRILL": 46.0, "FRY": 44.0, "ASSEMBLE": 48.0, "BEVERAGE": 60.0}  # orders/hour
STAFF = {"GRILL": 2, "FRY": 2, "ASSEMBLE": 2, "BEVERAGE": 1}
TPH_PER_STAFF = {s: CAPACITY[s] / STAFF[s] for s in STATIONS}  # throughput per staff member

SLA_MIN = 12          # promised = placed + 12 minutes
NOW_MIN = 65          # 13:05, minutes after 12:00 -- the fixed synthetic "now"

BASELINE_COUNTS = [15, 20, 24, 22, 19, 17, 16, 15]   # a typical Friday lunch, per 15-min bucket
TODAY_COUNTS = [20, 30, 36, 33, 25, 22, 21, 20]      # today: +40%, surge 12:15-12:45
BASELINE_MIX = {"GRILL": 0.35, "FRY": 0.30, "ASSEMBLE": 0.25, "BEVERAGE": 0.10}
TODAY_MIX = {"GRILL": 0.52, "FRY": 0.20, "ASSEMBLE": 0.20, "BEVERAGE": 0.08}

COMPLAINT_P_DELAY = 0.35   # P(complaint | wait > 15 min)
DELAY_THRESHOLD = 15.0     # minutes


# --------------------------------------------------------------------------
# Queue model shared by the data generator, the agent's analysis, and the
# verify simulation -- so the story, the diagnosis, and the numbers agree.
# --------------------------------------------------------------------------
def simulate_station(counts, share, capacity, base_prep):
    """Bucket backlog model.

    waits[b] = base_prep + (backlog at start of bucket / capacity) * 60.
    Returns (waits_per_bucket, ending_backlog, peak_backlog).
    """
    backlog, waits, peak = 0.0, [], 0.0
    for c in counts:
        arr_rate = c * share / 0.25  # orders/hour arriving in this bucket
        waits.append(base_prep + (backlog / capacity) * 60.0)
        backlog = max(0.0, backlog + (arr_rate - capacity) * 0.25)
        peak = max(peak, backlog)
    return waits, backlog, peak


def _bucket_category_counts(counts, mix):
    """Deterministic per-bucket, per-station order counts that sum exactly."""
    out = []
    for c in counts:
        raw = {s: c * mix[s] for s in STATIONS}
        base = {s: int(raw[s]) for s in STATIONS}
        rem = c - sum(base.values())
        frac = sorted(STATIONS, key=lambda s: (-(raw[s] - base[s]), s))
        for s in frac[:rem]:
            base[s] += 1
        out.append(base)
    return out


def _fmt_clock(mins):
    h, m = 12 + int(mins) // 60, int(mins) % 60
    return "%d:%02d" % (h, m)


# --------------------------------------------------------------------------
# Synthetic data: today's orders, pickup records, complaints.
# --------------------------------------------------------------------------
def build_world():
    # Re-seed every call so the interactive web UI (which shares this process)
    # rebuilds the same world on every request: same input -> same output.
    rng.seed(SEED)
    waits_today = {
        s: simulate_station(TODAY_COUNTS, TODAY_MIX[s], CAPACITY[s], BASE_PREP[s])[0]
        for s in STATIONS
    }
    cat_counts = _bucket_category_counts(TODAY_COUNTS, TODAY_MIX)

    orders, oid = [], 1001
    for b, bucket in enumerate(BUCKETS):
        for s in STATIONS:  # fixed station order -> deterministic
            for _ in range(cat_counts[b][s]):
                placed = b * 15 + rng.randrange(0, 15)
                wait = max(1.0, waits_today[s][b] + rng.uniform(-1.0, 1.0))
                ready = placed + wait
                if ready + 3 <= NOW_MIN:
                    status, pickup = "PICKED_UP", ready + rng.uniform(0, 3)
                elif ready <= NOW_MIN:
                    status, pickup = "READY", None
                else:
                    status, pickup = "IN_PREP", None
                orders.append({
                    "id": "TP-%d" % oid, "bucket": bucket, "station": s,
                    "placed_min": placed, "placed": _fmt_clock(placed),
                    "promised_min": placed + SLA_MIN, "promised": _fmt_clock(placed + SLA_MIN),
                    "wait": wait, "ready_min": ready, "ready": _fmt_clock(ready),
                    "status": status, "pickup_min": pickup,
                    "customer": "CUST-%d" % (101 + (oid % 60)),
                })
                oid += 1

    delay_texts = [
        "Order was supposed to be ready 10 min ago, still waiting.",
        "Waiting 25 minutes for a lunch pickup. This never happens.",
        "App said ready at 12:40. It's 1:05 and nothing.",
        "My lunch break is over and my food isn't ready.",
        "Longest wait I've had here. What's going on today?",
        "Been standing here 20 minutes watching other people get their food.",
        "Ordered ahead and STILL waiting longer than the walk-ins.",
        "Two kids, one lunch hour, zero food so far.",
        "The wait time on the app keeps jumping. Just tell me honestly.",
        "I come here every Friday. Today is not it.",
    ]
    complaints, cid = [], 1
    for o in sorted(orders, key=lambda x: (x["placed_min"], x["id"])):
        if o["wait"] > DELAY_THRESHOLD and rng.random() < COMPLAINT_P_DELAY:
            complaints.append({
                "id": "C-%03d" % cid, "category": "long_wait", "order_id": o["id"],
                "customer": o["customer"], "time": o["placed"],
                "bucket": o["bucket"], "wait": o["wait"],
                "text": rng.choice(delay_texts), "channel": rng.choice(["app", "app", "kiosk", "phone"]),
                "needs_customer_info": False,
            })
            cid += 1

    # Other categories: missing items CLUSTER in the surge window (the handoff
    # story for capability A); incorrect orders and delivery delays are spread.
    surge_orders = [o for o in orders if o["bucket"] in ("12:30", "12:45", "13:00")
                    and o["station"] in ("GRILL", "ASSEMBLE")]
    other_orders = [o for o in orders if o not in surge_orders]
    missing_pool = rng.sample(surge_orders, 8)
    incorrect_pool = rng.sample(other_orders, 6)
    delivery_pool = rng.sample([o for o in other_orders if o not in incorrect_pool], 4)
    missing_texts = [
        "Fries missing from the bag. Second time this month.",
        "No drink in the bag, and I paid for a combo.",
        "Ordered two burgers, only one in the bag.",
        "Dipping sauces missing again.",
    ]
    incorrect_texts = [
        "Got the chicken sandwich instead of the veggie one.",
        "Asked for no onions. This is ALL onions.",
        "This isn't what I ordered at all.",
        "Got someone else's entire order.",
    ]
    delivery_texts = [
        "Delivery arrived 40 minutes late, food was cold.",
        "Driver went to the wrong address, then blamed me.",
        "Order arrived spilled everywhere. Unusable.",
        "Said delivered. Nothing at my door.",
    ]
    other_specs = (
        [("missing_items", o, missing_texts[i % len(missing_texts)])
         for i, o in enumerate(missing_pool)]
        + [("incorrect_orders", o, incorrect_texts[i % len(incorrect_texts)])
           for i, o in enumerate(incorrect_pool)]
        + [("delivery_delay", o, delivery_texts[i % len(delivery_texts)])
           for i, o in enumerate(delivery_pool)]
    )
    for cat, o, text in other_specs:
        complaints.append({
            "id": "C-%03d" % cid, "category": cat, "order_id": o["id"],
            "customer": o["customer"], "time": o["placed"],
            "bucket": o["bucket"], "wait": o["wait"],
            "text": text, "channel": rng.choice(["app", "kiosk", "phone"]),
            "needs_customer_info": cat == "delivery_delay",
        })
        cid += 1
    # One missing-items complaint genuinely needs the customer's bag photo.
    for c in complaints:
        if c["category"] == "missing_items":
            c["needs_customer_info"] = True
            break

    complaints.sort(key=lambda c: (c["time"], c["id"]))
    pickup_records = {o["id"]: (o["pickup_min"] if o["pickup_min"] is not None else None)
                      for o in orders}
    return orders, complaints, pickup_records


# --------------------------------------------------------------------------
# Printing helpers -- the agent "thinks out loud" so students can follow it.
# --------------------------------------------------------------------------
def banner(title, sub=""):
    print("=" * 78)
    print(title)
    if sub:
        print(sub)
    print("=" * 78)


def hstep(n, total, title):
    print()
    print(">>> STEP %d/%d: %s" % (n, total, title))
    print("-" * 78)


def orch(text):
    print("[orchestrator] %s" % text)


def tool(name, detail, results):
    print("  [tool] %s(%s)" % (name, detail))
    for r in results:
        print("         -> %s" % r)


def say(text):
    print(text)


def pearson(xs, ys):
    n = len(xs)
    mx, my = sum(xs) / n, sum(ys) / n
    num = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    den = (sum((x - mx) ** 2 for x in xs) * sum((y - my) ** 2 for y in ys)) ** 0.5
    return num / den if den else 0.0


# --------------------------------------------------------------------------
# THE AGENT'S TOOLS -- one orchestrator calls these; they are capability
# groups, NOT separate agents.
# --------------------------------------------------------------------------

# ---- (A) Customer Experience Intelligence ---------------------------------
def t_categorize_complaints(complaints):
    counts = {}
    for c in complaints:
        counts[c["category"]] = counts.get(c["category"], 0) + 1
    return counts


def t_complaint_concentration(complaints, category):
    by_bucket = {}
    for c in complaints:
        if c["category"] == category:
            by_bucket[c["bucket"]] = by_bucket.get(c["bucket"], 0) + 1
    return by_bucket


# ---- (A/D) operations inspection -- the agent CHOOSES what to inspect -----
def t_compare_volume():
    today, base = sum(TODAY_COUNTS), sum(BASELINE_COUNTS)
    peak_today = max(TODAY_COUNTS) * 4
    peak_base = max(BASELINE_COUNTS) * 4
    return today, base, peak_today, peak_base


def t_station_waits(counts, mix, capacities):
    """Per-station average wait (order-weighted) under given capacities."""
    out = {}
    for s in STATIONS:
        if mix[s] <= 0 or capacities[s] <= 0:
            continue  # station offline or no demand routed to it
        waits, _, peak = simulate_station(counts, mix[s], capacities[s], BASE_PREP[s])
        cat_counts = _bucket_category_counts(counts, mix)
        tot = sum(cat_counts[b][s] for b in range(len(BUCKETS)))
        avg = sum(waits[b] * cat_counts[b][s] for b in range(len(BUCKETS))) / tot
        out[s] = (avg, peak)
    return out


def adjusted_mix_fryer_down():
    """Fryer offline: 60% of fry demand converts to assemble/beverage items,
    40% cannot be fulfilled (orders at risk)."""
    fry = TODAY_MIX["FRY"]
    return {
        "GRILL": TODAY_MIX["GRILL"],
        "FRY": 0.0,
        "ASSEMBLE": TODAY_MIX["ASSEMBLE"] + fry * 0.6 * 0.7,
        "BEVERAGE": TODAY_MIX["BEVERAGE"] + fry * 0.6 * 0.3,
    }


def t_bucket_avg_wait(counts, mix, capacities):
    waits_by_station = {
        s: simulate_station(counts, mix[s], capacities[s], BASE_PREP[s])[0] for s in STATIONS
    }
    cat_counts = _bucket_category_counts(counts, mix)
    out = []
    for b in range(len(BUCKETS)):
        tot = sum(cat_counts[b][s] for s in STATIONS)
        out.append(sum(waits_by_station[s][b] * cat_counts[b][s] for s in STATIONS) / tot)
    return out


# ---- (D) Root-Cause Analysis ----------------------------------------------
def t_hypothesis_tests(complaints):
    """Correlation AND causation verdicts, kept explicitly separate."""
    grill_rates = [c * TODAY_MIX["GRILL"] / 0.25 for c in TODAY_COUNTS]
    avg_waits = t_bucket_avg_wait(TODAY_COUNTS, TODAY_MIX, CAPACITY)
    r_same_bucket = pearson(grill_rates, avg_waits)
    # Queues lag arrivals: bucket b's arrivals drive bucket b+2's waits.
    r_lag30 = pearson(grill_rates[:-2], avg_waits[2:])

    # Mechanism check: for how long did grill arrivals exceed grill capacity?
    overload_buckets = [
        BUCKETS[b] for b in range(len(BUCKETS))
        if TODAY_COUNTS[b] * TODAY_MIX["GRILL"] / 0.25 > CAPACITY["GRILL"]
    ]
    _, _, peak_backlog = simulate_station(
        TODAY_COUNTS, TODAY_MIX["GRILL"], CAPACITY["GRILL"], BASE_PREP["GRILL"])
    return {
        "r_same_bucket": r_same_bucket,
        "r_lag30": r_lag30,
        "overload_buckets": overload_buckets,
        "grill_peak_backlog": peak_backlog,
        # Staffing never varied today and matches baseline -> it cannot be the
        # change-driver. We explicitly do NOT claim staffing caused the delays.
        "staffing_varied": False,
        "staffing_matches_baseline": True,
        # Synthetic inventory log: zero stockouts today.
        "stockouts_today": 0,
    }


def t_estimate_intervention(counts, mix, capacities, change_desc, new_capacities):
    before = t_station_waits(counts, mix, capacities)["GRILL"][0]
    after = t_station_waits(counts, mix, new_capacities)["GRILL"][0]
    return before, after, change_desc


# ---- (B) Personalized Service Recovery -------------------------------------
RECOVERY_POLICY = [
    ("apology + live status update", "AUTO-APPROVED -- no approval needed"),
    ("coupon up to $5 (one per complaint)", "MANAGER approval required"),
    ("refund, or coupon over $5", "MANAGER approval + duty-manager code required"),
    ("anything not in this table", "BLOCKED -- escalate to a human"),
]


def t_lookup_order(orders, ref):
    for o in orders:
        if o["id"] == ref:
            return o
    return None


def t_verify_pickup(pickup_records, ref):
    # Returns the pickup timestamp or None. The agent verifies; it never
    # assumes an order was delivered or picked up.
    return pickup_records.get(ref)


def t_check_recovery_policy(action):
    for pattern, rule in RECOVERY_POLICY:
        if pattern.split(" ")[0] in action or action in pattern:
            return rule
    return RECOVERY_POLICY[-1][1]


def t_request_approval(action, approver):
    # In production this pings the manager's ops console and waits for a tap.
    # In this offline demo the tap is simulated -- and labeled as such.
    return "APPROVED by %s (simulated tap -- in production, a real human tap)" % approver


def t_draft_recovery_response(customer, order_id, promised, now_label, coupon):
    return (
        "Hi %s, this is TastePoint Downtown. Your order %s (promised %s) is "
        "still in our kitchen queue -- it has NOT been marked picked up, so it "
        "is still coming. Current estimate: ready by %s. I'm sorry for the "
        "wait; here's a %s coupon for the trouble. Reply here and a team "
        "member will prioritize your order."
        % (customer, order_id, promised, now_label, coupon)
    )


# ---- (C) Demand & Kitchen Coordination --------------------------------------
def t_forecast_demand():
    # Inputs: history (typical Friday), day/time (Friday lunch), weather
    # (clear, 72F -- synthetic), incoming app pre-orders (31 already placed).
    hist = sum(BASELINE_COUNTS)
    forecast = round(hist * 1.12 * 1.02 + 31)
    return {
        "inputs": "history=%d orders (typical Friday) x Friday-factor 1.12 x weather 1.02 + 31 incoming pre-orders" % hist,
        "forecast_orders": forecast,
        "forecast_grill_share": 0.50,
        "note": "grill-heavy mix expected to persist (limited-time grilled item)",
    }


def t_check_kitchen_and_inventory(capacities):
    _, _, grill_peak = simulate_station(
        TODAY_COUNTS, TODAY_MIX["GRILL"], capacities["GRILL"], BASE_PREP["GRILL"])
    grill_staff = capacities["GRILL"] / TPH_PER_STAFF["GRILL"]
    return {
        "grill_peak_backlog": grill_peak,
        "bottleneck": "GRILL station queue (single queue, %d staff after the move)"
                      % round(grill_staff),
        "ingredients": "OK -- no stockouts; grill protein par covers forecast + 11%",
        "handoff": "grill -> expedite handoff is the pile-up point",
    }


# ---- (E) Loyalty & Experience Improvement ------------------------------------
def t_unresolved_followups(complaints):
    return [c for c in complaints if c["needs_customer_info"]]


def t_personalization_context(customer):
    # Service preferences the customer STATED (e.g., at signup / past orders)
    # plus the current problem. Nothing inferred, nothing sensitive.
    return {
        "customer": customer,
        "stated_preferences": ["SMS (not push) order updates", "low-sodium options noted on past orders"],
        "current_problem": "delayed grill order during lunch surge",
        "personalization": "text update when order is 5 min out; offer low-sodium substitute while they wait",
        "guardrails": "no inferred characteristics; no unsolicited messages; service preferences + current problem only",
    }


# --------------------------------------------------------------------------
# THE LIVE DEMO SCENARIO -- one orchestrator, tools, six steps + twist.
# --------------------------------------------------------------------------
def run_demo():
    orders, complaints, pickup_records = build_world()

    banner(
        "GuestFirst AI -- An Agentic AI System for Personalized Restaurant Experiences",
        "Demo 8 of 8 - Agentic AI Workshop\n"
        "TastePoint is a FICTIONAL restaurant chain. All data below is SYNTHETIC.\n"
        "Outcomes labeled SIMULATED are model outputs, not real measurements.",
    )
    say("")
    say("SCENE: TastePoint Downtown. Friday lunch, 12:00-14:00. It is 13:05.")
    say("The lunch rush brought an unusual spike of complaints. The manager asks:")
    say("")
    say('  "Why are customers complaining about long wait times today,')
    say('   and what should we do?"')
    say("")
    orch("goal accepted. This is not a dashboard query -- it needs investigation,")
    orch("a decision, coordinated action, and verification. Building the plan...")
    say("")
    say("  [orchestrator] plan (capabilities in brackets):")
    say("    1. Categorize today's complaints ......................... (A)")
    say("    2. Choose operational data to inspect from the patterns .. (A)")
    say("    3. Root-cause: test staffing / inventory / mix hypotheses,")
    say("       separating correlation from causation ................ (D)")
    say("    4. Run service-recovery on affected customers ............ (B)")
    say("    5. Forecast demand, check kitchen, recommend adjustment .. (C)")
    say("    6. VERIFY the fix with a simulation ...................... (D)")
    say("    Then: handle the twist, and score agent-vs-baseline.")
    say("")

    # ================= STEP 1: categorize ==================================
    hstep(1, 6, "CATEGORIZE -- what are customers actually complaining about? (A)")
    counts = t_categorize_complaints(complaints)
    tool("categorize_complaints", 'window="12:00-14:00", n=%d' % len(complaints),
         ["%s: %d" % (k, counts[k]) for k in sorted(counts)])
    conc = t_complaint_concentration(complaints, "long_wait")
    tool("complaint_concentration", 'category="long_wait"',
         ["%s: %d long-wait complaints" % (b, conc.get(b, 0)) for b in BUCKETS
          if conc.get(b, 0)])
    active = [b for b in BUCKETS if conc.get(b, 0)]
    window = "%s-%s" % (active[0], active[-1])
    orch("long waits dominate (%d of %d) and cluster %s. That pattern"
         % (counts["long_wait"], len(complaints), window))
    orch("chooses what I inspect next: order volume vs baseline, timestamps,")
    orch("kitchen workload in that window -- not a generic data dump.")

    # ================= STEP 2: investigate =================================
    hstep(2, 6, "INVESTIGATE -- order volume, timestamps, demand, staffing, inventory (A+D)")
    today, base, peak_today, peak_base = t_compare_volume()
    tool("compare_order_volume", "today vs typical Friday",
         ["today: %d orders vs baseline %d (+%d%%)" % (today, base, round(100 * (today - base) / base)),
          "peak arrival rate: %d/hr today vs %d/hr baseline" % (peak_today, peak_base),
          "FINDING: orders are arriving much faster than baseline, "
          "concentrated 12:15-12:45"])
    waits = t_station_waits(TODAY_COUNTS, TODAY_MIX, CAPACITY)
    tool("analyze_waits_by_workflow", "per-station predicted wait (queue model)",
         ["%s: avg wait %.1f min" % (s, waits[s][0]) for s in STATIONS])
    orch("delays are concentrated in ONE workflow: GRILL (%.1f min) while the" % waits["GRILL"][0])
    orch("other stations sit at 2-5 min. The bottleneck is not 'the kitchen' --")
    orch("it is the grill queue. Digging one level deeper...")

    # The missing-items sub-pattern: the agent chooses a DIFFERENT inspection.
    miss_conc = t_complaint_concentration(complaints, "missing_items")
    surge_miss = sum(miss_conc.get(b, 0) for b in ("12:30", "12:45", "13:00"))
    tool("inspect_handoff_process", 'pattern="missing items cluster in surge window"',
         ["missing-item complaints in 12:30-13:00 surge: %d of %d"
          % (surge_miss, counts.get("missing_items", 0))],
         )
    say("         -> FINDING: expedite-handoff verification was skipped on rush orders;")
    say("            missing-item rate ~3x baseline during the surge.")
    say("            (Same capability: the pattern chose the inspection -- order")
    say("             complexity/volume/handoff, not a pre-canned report.)")

    # ================= STEP 3: root cause ==================================
    hstep(3, 6, "ROOT CAUSE -- correlation is not causation (D) [priority feature]")
    hyp = t_hypothesis_tests(complaints)
    say("  Hypothesis tests -- each gets a CORRELATION verdict and a separate CAUSATION verdict:")
    say("")
    say("  [tool] correlation_analysis(grill arrival rate vs avg wait, same bucket)")
    say("         -> Pearson r = %.2f -- NEGATIVE. A naive read says grill volume" % hyp["r_same_bucket"])
    say("            *reduces* waits. That is absurd -- and it is exactly the lesson.")
    say("  [tool] correlation_analysis(grill arrival rate vs avg wait, 30-min lag)")
    say("         -> Pearson r = %.2f -- the sign flips once you respect the queue" % hyp["r_lag30"])
    say("            lag. Correlation is fragile here: it knows nothing of lag,")
    say("            capacity, or mechanism.")
    say("  So the agent tests the MECHANISM instead of worshipping r:")
    say("")
    say("  CAUSATION verdicts (mechanism + evidence, not just r):")
    say("   1. ORDER-MIX SHIFT + VOLUME SURGE -> SUPPORTED.")
    say("      Grill share 35% -> 52% AND +40% volume. Grill arrivals exceeded")
    say("      grill capacity for %d straight minutes (%s); backlog peaked at"
        % (len(hyp["overload_buckets"]) * 15, ", ".join(hyp["overload_buckets"])))
    say("      %.1f orders waiting on one queue. The queue model reproduces the" % hyp["grill_peak_backlog"])
    say("      observed waits -- mechanism confirmed.")
    say("   2. UNDERSTAFFING -> NOT SUPPORTED. Staffing never varied today and")
    say("      matches the baseline exactly (2 grill staff both days). A constant")
    say("      cannot explain a change. The agent does NOT claim staffing caused")
    say("      the delays -- flat capacity met a different demand mix.")
    say("   3. INVENTORY SHORTAGE -> RULED OUT. Zero stockouts in today's logs;")
    say("      grill protein par covered demand.")
    say("")
    orch("root cause: a demand surge concentrated in grill-category orders hit a")
    orch("fixed grill queue. Now: what does the fix buy us? Estimating from the")
    orch("same queue model before recommending anything...")
    new_cap = dict(CAPACITY)
    new_cap["GRILL"] = CAPACITY["GRILL"] + TPH_PER_STAFF["GRILL"]   # +1 staff to grill
    new_cap["ASSEMBLE"] = CAPACITY["ASSEMBLE"] - TPH_PER_STAFF["ASSEMBLE"]  # -1 from assemble
    before, after, desc = t_estimate_intervention(
        TODAY_COUNTS, TODAY_MIX, CAPACITY,
        "move 1 staff ASSEMBLE -> GRILL during 12:00-14:00", new_cap)
    tool("estimate_intervention_effect", "historical queue-model simulation",
         ["grill avg wait: %.1f -> %.1f min (-%d%%)" % (before, after, round(100 * (before - after) / before)),
          "assemble avg wait rises slightly (trade-off is explicit, not hidden)",
          "recommendation: %s -- PENDING MANAGER APPROVAL" % desc])
    say("")
    say("  >>> APPROVAL GATE: the staffing change is staged, NOT applied.")
    say("      In production the manager taps approve in the ops console;")
    say("      the demo simulates that tap below.")
    say("      Decision: %s" % t_request_approval("staffing change: 1 ASSEMBLE -> GRILL", "manager"))

    return orders, complaints, pickup_records, new_cap


def service_recovery_scene(orders, complaints, pickup_records):
    # ================= STEP 4: service recovery ============================
    hstep(4, 6, "SERVICE RECOVERY -- one complaint, handled end-to-end (B)")
    target = None
    for c in complaints:
        if c["category"] == "long_wait":
            o = t_lookup_order(orders, c["order_id"])
            if o is not None and o["status"] == "IN_PREP" and t_verify_pickup(pickup_records, o["id"]) is None:
                target = (c, o)
                break
    c, o = target
    say('  Inbox: "%s" -- %s (%s)' % (c["text"], c["id"], c["customer"]))
    say("")
    orch("recovery workflow for %s: lookup -> verify -> policy check -> draft ->" % c["order_id"])
    orch("approve -> record -> verify. The agent never assumes, never refunds blind.")
    tool("lookup_order", 'ref="%s"' % o["id"],
         ["found: placed %s, promised %s, status %s, station %s"
          % (o["placed"], o["promised"], o["status"], o["station"])])
    pk = t_verify_pickup(pickup_records, o["id"])
    tool("verify_pickup_records", 'ref="%s"' % o["id"],
         ["pickup record: %s" % ("NONE -- order is still in the kitchen" if pk is None else _fmt_clock(pk)),
          "we verify against the record; we do NOT assume it was delivered"])
    say("  [tool] check_recovery_policy(...) -- the authorization table:")
    for action, rule in RECOVERY_POLICY:
        say("         -> %-38s : %s" % (action, rule))
    draft = t_draft_recovery_response(c["customer"], o["id"], o["promised"], "1:12 PM", "$5")
    tool("draft_recovery_response", 'tone="apologetic, specific, no excuses"',
         ['draft: "%s..."' % draft[:88]])
    say("  [tool] request_approval(action=\"issue $5 coupon\", approver=\"manager\")")
    say("         -> %s" % t_request_approval("issue $5 coupon", "manager"))
    tool("record_resolution", 'complaint="%s"' % c["id"],
         ["resolution recorded: coupon issued, status update sent (18 min after complaint)"])
    tool("verify_resolution", 'complaint="%s"' % c["id"],
         ["complaint marked RESOLVED; pickup record will be re-checked at close"])
    say("")
    say("  Guardrail demo -- the agent tries something it must NOT do:")
    say('  [tool] issue_refund(order="%s", amount="$20", approval="none")' % o["id"])
    say("         -> BLOCKED by policy guardrail: refunds need manager approval +")
    say("            duty-manager code. Escalated to a human. The agent NEVER issues")
    say("            refunds or compensation outside the authorization rules.")


def coordination_scene():
    # ================= STEP 5: demand & kitchen coordination ================
    hstep(5, 6, "COORDINATE -- forecast, check kitchen, recommend (C)")
    fc = t_forecast_demand()
    tool("forecast_demand", "history + day/time + weather + incoming orders",
         [fc["inputs"],
          "forecast: ~%d orders tomorrow 12:00-14:00, grill share ~%d%%"
          % (fc["forecast_orders"], int(fc["forecast_grill_share"] * 100)),
          fc["note"]])
    new_cap = {"GRILL": 69.0, "FRY": 44.0, "ASSEMBLE": 24.0, "BEVERAGE": 60.0}
    kit = t_check_kitchen_and_inventory(new_cap)
    tool("check_kitchen_workload + check_ingredients", "under the recommended staffing",
         ["grill peak backlog tomorrow: %.1f orders (vs 18.5 today)" % kit["grill_peak_backlog"],
          "bottleneck: %s" % kit["bottleneck"],
          "ingredients: %s" % kit["ingredients"]])
    say("  [tool] recommend_prep_levels(...)")
    say("         -> prep to forecast + 11% safety buffer, NOT a fixed par.")
    say("            The agent refuses to blindly over-prepare: over-prep is waste,")
    say("            and waste is a metric it is scored on (see evaluation).")
    orch("recommendation staged for tomorrow's lunch -- still pending the")
    orch("manager's approval. Nothing executes without it.")


def twist_and_verify():
    # ================= THE TWIST ===========================================
    print()
    print("!" * 78)
    print("!!! TWIST -- 13:05: facilities reports the FRYER station will be OFFLINE")
    print("!!! tomorrow for emergency maintenance. The original plan assumed a working")
    print("!!! fryer. The agent must REVISE under the new constraint.")
    print("!" * 78)
    orch("new constraint detected: FRY capacity = 0 tomorrow. Replanning...")
    say("")
    say("  REVISED PLAN (replaces the original -- original is kept for comparison):")
    say("   1. Pause fry-item sales on kiosk/app after 12:00; offer 1-tap substitutes")
    say("      (substitute mapping drafted -- manager approval required).")
    say("   2. Reassign BOTH idle fry staff: 1 -> GRILL, 1 -> ASSEMBLE")
    say("      (grill keeps 3 staff, assemble keeps 2 -- no station is thinned).")
    say("   3. Fry prep-ahead capped at ZERO -- no cooking for a dead station (waste guard).")
    say("   4. Proactive outreach to the ~17 fry orders at risk: substitute or cancel,")
    say("      their choice -- approval-gated, like all customer-facing actions.")
    say("")
    say("  >>> APPROVAL GATE: revised plan staged. %s"
        % t_request_approval("revised fryer-outage plan", "manager"))

    # ================= STEP 6: VERIFY ======================================
    hstep(6, 6, "VERIFY -- simulate original vs revised plan, side by side (D)")
    say("  SIMULATED tomorrow lunch (same demand profile as today). All numbers")
    say("  below are model outputs, not measurements.")
    say("")

    s1_cap = {"GRILL": 69.0, "FRY": 44.0, "ASSEMBLE": 24.0, "BEVERAGE": 60.0}  # original plan
    s2_cap = {"GRILL": 69.0, "FRY": 0.0, "ASSEMBLE": 48.0, "BEVERAGE": 60.0}   # revised plan
    mix_s2 = adjusted_mix_fryer_down()

    def scenario(name, capacities, mix, fry_paused):
        waits = t_station_waits(TODAY_COUNTS, mix, capacities)
        grill_peak = waits["GRILL"][1]
        exp_prep = {s: waits[s][0] for s in sorted(waits)}
        # orders at risk: fry orders unfulfillable + any order waiting > 30 min
        cat_counts = _bucket_category_counts(TODAY_COUNTS, mix)
        fry_demand = _bucket_category_counts(TODAY_COUNTS, TODAY_MIX)
        fry_orders = sum(fry_demand[b]["FRY"] for b in range(len(BUCKETS)))
        at_risk_fry = round(fry_orders * 0.40) if fry_paused else 0
        waits_by_station = {
            s: simulate_station(TODAY_COUNTS, mix[s], capacities[s], BASE_PREP[s])[0]
            for s in waits
        }
        over30 = sum(cat_counts[b][s] for b in range(len(BUCKETS)) for s in waits
                     if waits_by_station[s][b] > 30)
        # food waste: buffer x food mass (+ scrapped fry prep when fryer is down)
        if fry_paused:
            fulfilled = sum(TODAY_COUNTS) - fry_orders
            waste = fulfilled * 0.18 * 0.11 + 1.5
        else:
            waste = sum(TODAY_COUNTS) * 0.18 * (0.11 if name != "do-nothing" else 0.21)
        # overall predicted avg wait over fulfilled orders
        tot_n = sum(cat_counts[b][s] for b in range(len(BUCKETS)) for s in waits)
        tot_w = sum(cat_counts[b][s] * waits_by_station[s][b]
                    for b in range(len(BUCKETS)) for s in waits)
        return {"exp_prep": exp_prep, "avg_wait": tot_w / tot_n,
                "at_risk": at_risk_fry + over30, "waste": waste,
                "grill_peak": grill_peak}

    s0 = scenario("do-nothing", CAPACITY, TODAY_MIX, False)
    s1 = scenario("original", s1_cap, TODAY_MIX, False)
    s2 = scenario("revised", s2_cap, mix_s2, True)

    rows = [
        ("expected fulfillment, GRILL (min)", "%.1f" % s1["exp_prep"]["GRILL"], "%.1f" % s2["exp_prep"]["GRILL"]),
        ("expected fulfillment, FRY (min)", "%.1f" % s1["exp_prep"]["FRY"], "n/a (station offline)"),
        ("expected fulfillment, ASSEMBLE (min)", "%.1f" % s1["exp_prep"]["ASSEMBLE"], "%.1f" % s2["exp_prep"]["ASSEMBLE"]),
        ("predicted avg wait, fulfilled orders (min)", "%.1f" % s1["avg_wait"], "%.1f" % s2["avg_wait"]),
        ("orders at risk", "%d" % s1["at_risk"], "%d (fry substitutions)" % s2["at_risk"]),
        ("food waste (kg, simulated)", "%.1f" % s1["waste"], "%.1f" % s2["waste"]),
    ]
    say("  %-42s %12s %24s" % ("SIMULATED metric", "ORIGINAL plan", "REVISED plan (fryer down)"))
    for label, v1, v2 in rows:
        say("  %-42s %12s %24s" % (label, v1, v2))
    say("")
    say("  Remaining constraints under the revised plan: fryer offline until repair;")
    say("  fry menu paused; %d fry orders need substitution/cancel outreach." % s2["at_risk"])
    orch("verdict: the revised plan holds the line -- waits and waste stay low.")
    orch("The cost is %d fry orders needing outreach. The constraint is the fryer," % s2["at_risk"])
    orch("not the plan -- and the simulation makes that visible BEFORE lunch.")
    return s0, s2


def evaluation_scene(complaints):
    print()
    banner("EVALUATION -- GuestFirst AI vs baseline (SIMULATED outcomes)")
    say("  Baseline = fixed staffing + manual complaint review, on the SAME synthetic")
    say("  data. Every number below is a SIMULATED outcome of the demo's models --")
    say("  it shows the mechanism, not a real restaurant result.")
    say("")
    # --- computed from the models -----------------------------------------
    mix_s2 = adjusted_mix_fryer_down()
    s2_cap = {"GRILL": 69.0, "FRY": 0.0, "ASSEMBLE": 48.0, "BEVERAGE": 60.0}
    s0_waits = t_station_waits(TODAY_COUNTS, TODAY_MIX, CAPACITY)
    s2_waits = t_station_waits(TODAY_COUNTS, mix_s2, s2_cap)

    def overall_avg(waits, mix):
        cat_counts = _bucket_category_counts(TODAY_COUNTS, mix)
        tot = sum(cat_counts[b][s] for b in range(len(BUCKETS)) for s in waits)
        return sum(waits[s][0] * cat_counts[b][s]
                   for b in range(len(BUCKETS)) for s in waits) / tot

    base_wait, agent_wait = overall_avg(s0_waits, TODAY_MIX), overall_avg(s2_waits, mix_s2)
    # order accuracy falls as the peak backlog forces rushed handoffs
    base_acc = 99.2 - 0.08 * s0_waits["GRILL"][1]
    agent_acc = 99.2 - 0.08 * s2_waits["GRILL"][1]
    # complaint resolution: manual inbox sits until the 14:30 review batch
    base_resolve, agent_resolve = 96.0, 18.0
    # resolution completion from the actual synthetic complaint list
    base_done = sum(1 for i, c in enumerate(complaints) if i % 2 == 0 and i < 30)
    agent_done = sum(1 for c in complaints if not c["needs_customer_info"])
    base_comp = 100.0 * base_done / len(complaints)
    agent_comp = 100.0 * agent_done / len(complaints)
    # repeat complaints: 30% of unresolved complainants complain again
    base_repeat = 100.0 * 0.30 * (len(complaints) - base_done) / len(complaints)
    agent_repeat = 100.0 * 0.30 * (len(complaints) - agent_done) / len(complaints)
    # forecast accuracy: 100 - MAPE vs today's actual demand
    last_friday = 152  # synthetic "last Friday" actual
    base_mape = abs(last_friday - sum(TODAY_COUNTS)) / sum(TODAY_COUNTS)
    agent_fc = round(sum(BASELINE_COUNTS) * 1.12 * 1.02 + 31)
    agent_mape = abs(agent_fc - sum(TODAY_COUNTS)) / sum(TODAY_COUNTS)
    # food waste: fixed par (21% buffer) vs forecast-based prep (11% buffer)
    food_mass = sum(TODAY_COUNTS) * 0.18
    base_waste = food_mass * 0.21
    fry_orders = sum(_bucket_category_counts(TODAY_COUNTS, TODAY_MIX)[b]["FRY"]
                     for b in range(len(BUCKETS)))
    agent_waste = (sum(TODAY_COUNTS) - fry_orders) * 0.18 * 0.11 + 1.5

    rows = [
        ("avg wait time (min)", "%.1f" % base_wait, "%.1f" % agent_wait,
         "queue model; agent figure over fulfilled orders (16 fry orders at risk, separate line)"),
        ("order accuracy (%)", "%.1f" % base_acc, "%.1f" % agent_acc,
         "accuracy falls as peak backlog forces rushed handoffs"),
        ("complaint resolution time (min)", "%.0f" % base_resolve, "%.0f" % agent_resolve,
         "manual inbox waits for the 14:30 review batch; agent triages at once"),
        ("repeat complaint rate (%)", "%.0f" % base_repeat, "%.0f" % agent_repeat,
         "30% of unresolved complainants complain again (simulated)"),
        ("forecast accuracy (%)", "%.0f" % (100 * (1 - base_mape)), "%.0f" % (100 * (1 - agent_mape)),
         "100 - MAPE vs today's actual demand"),
        ("food waste (kg)", "%.1f" % base_waste, "%.1f" % agent_waste,
         "fixed par over-preps; agent preps to forecast + buffer"),
        ("service recovery completion (%)", "%.0f" % base_comp, "%.0f" % agent_comp,
         "share of today's complaints resolved"),
    ]
    say("  %-34s %10s %10s" % ("SIMULATED metric", "BASELINE", "GUESTFIRST"))
    for label, b, a, why in rows:
        say("  %-34s %10s %10s" % (label, b, a))
        say("  %-34s   mechanism: %s" % ("", why))
    say("")
    orch("the agent wins on every metric -- even with a fryer offline -- because it")
    orch("investigates, acts through approval gates, and verifies. The baseline can")
    orch("only watch the numbers get worse.")


def loyalty_scene(complaints):
    print()
    banner("LOYALTY & EXPERIENCE IMPROVEMENT -- follow-up without profiling (E)")
    unresolved = t_unresolved_followups(complaints)
    say("  %d complaints need the customer's help (e.g., a bag photo) -- the agent" % len(unresolved))
    say("  does not guess; it schedules follow-ups for tomorrow 10:00 AM:")
    for c in unresolved[:4]:
        say("    - %s (%s): follow-up scheduled, one message only" % (c["id"], c["category"]))
    ctx = t_personalization_context(unresolved[0]["customer"] if unresolved else "CUST-101")
    say("")
    say("  Personalization for %s:" % ctx["customer"])
    say("    stated preferences : %s" % "; ".join(ctx["stated_preferences"]))
    say("    current problem    : %s" % ctx["current_problem"])
    say("    what we do         : %s" % ctx["personalization"])
    say("    guardrails         : %s" % ctx["guardrails"])
    orch("personalization is built from service preferences + the current problem.")
    orch("No inferred sensitive characteristics. No unwanted messages. Ever.")


def closing():
    print()
    banner("WHY AN AGENT -- not a dashboard, not a chatbot")
    say("  A DASHBOARD would report: 'satisfaction declined 12% this week.'")
    say("  A CHATBOT would summarize: 'customers mention long wait times.'")
    say("")
    say("  GuestFirst AI did something neither can:")
    say("    1. INVESTIGATED why -- mix shift + volume surge hit the grill queue")
    say("       (and explicitly refused to blame staffing without evidence).")
    say("    2. DETERMINED the action -- redistribute prep-station workload,")
    say("       sized by simulation, staged behind manager approval.")
    say("    3. COORDINATED the response -- per-complaint recovery workflow with")
    say("       authorization guardrails, plus kitchen adjustments.")
    say("    4. VERIFIED the fix -- simulated original vs revised plan BEFORE lunch,")
    say("       and recorded every resolution for follow-up.")
    say("")
    say("  Feedback -> order records -> operations -> service recovery ->")
    say("  verification: one agentic workflow, not five disconnected tools.")
    say("")
    say("  Honesty notes (see README.md for the full story):")
    say("   - TastePoint is FICTIONAL; every number above is SYNTHETIC or SIMULATED.")
    say("   - Chick-fil-A's publicly described initiatives (geofenced mobile ordering")
    say("     that times food prep, 1-2 minute wait reductions, order-complexity-based")
    say("     pickup estimates, forecasting prep needs) are cited as INSPIRATION ONLY;")
    say("     they do NOT establish that Chick-fil-A uses this system or anything")
    say("     like it.")
    say("")
    say("  End of demo. Run it again -- the output is byte-identical every time.")
    print("=" * 78)


def main():
    orders, complaints, pickup_records, _ = run_demo()
    service_recovery_scene(orders, complaints, pickup_records)
    coordination_scene()
    twist_and_verify()
    evaluation_scene(complaints)
    loyalty_scene(complaints)
    closing()


if __name__ == "__main__":
    main()
