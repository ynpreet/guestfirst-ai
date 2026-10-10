# GuestFirst AI — An Agentic AI System for Personalized Restaurant Experiences

**Demo 8 of 8 · Agentic AI Workshop**

> **FICTIONAL:** TastePoint is a fictional restaurant chain invented for this
> demo. Every order, complaint, timestamp, staff member, and metric in
> `demo.py` is **synthetic sample data** generated inside the file. Anything
> the demo labels **SIMULATED** is a model output, not a measurement of a
> real restaurant.

> **Open in Chrome (live web UI — the way to present this demo):**
>
> ```bash
> cd ~/workspace/agentic-ai-workshop/guestfirst-ai
> python3 app.py
> ```
>
> Then open **http://localhost:8008** in Chrome and click **"Run live demo"**.
> The page runs the real `demo.py` on your machine (via `GET /api/run`) and
> renders the orchestrator's plan, the styled agent trace (steps + tool
> calls), and a key-results panel — all offline, stdlib only, no API keys.
> If port 8008 is already taken, the server says so and exits; stop the
> other copy first.

---

## Real-world problem, target users, market need, and differentiation

**The problem.** It's Friday lunch at TastePoint Downtown. An unusual spike
of complaints hits the inbox, and the manager asks the only question that
matters:

> *"Why are customers complaining about long wait times today, and what
> should we do?"*

A dashboard would answer: *"Satisfaction declined 12%."* A chatbot would
answer: *"Customers mention long wait times."* Neither tells the manager
what to **do**.

**Target users.** Restaurant managers and multi-unit operators who own the
lunch rush — the people accountable for waits, waste, and recovery when
service breaks down.

**Market need.** When complaints spike, the clock is ticking: every minute
of wrong diagnosis is more angry customers and more waste. Managers need
the *why* (root cause), the *what* (the fix, sized before it's tried), and
the *proof* (verification before the next rush) — not another chart.

**Differentiation.** **GuestFirst AI** is an *agentic* system. One
orchestrator plans the investigation, calls tools to gather evidence, and
works the full loop: categorize → investigate → root-cause → recover →
coordinate → verify. Its signature move is intellectual honesty about
causation: the agent tests three hypotheses and keeps correlation and
causation explicitly separate. The punchline: naive correlation of grill
volume vs waits is **r = −0.43** (wrong sign!) because queues *lag*
arrivals; with a 30-minute lag it flips to **r = +0.50**. Correlation is
fragile here — so the agent tests the *mechanism*: grill arrivals exceeded
grill capacity for 45 straight minutes, backlog peaked at 18.5 orders.
Causation: **supported by mechanism, not by r.** Staffing is explicitly
*not* blamed (it never varied; a constant can't explain a change).
Inventory is ruled out (zero stockouts). And when the fryer goes offline
tomorrow, the agent *replans under the new constraint* and simulates
original vs revised plan before lunch — the difference between a script
and an agent.

---

## Meaningful Agentic AI functionality

**Why an agent — not a dashboard, not a chatbot:**

| | Dashboard | Chatbot | GuestFirst AI (agentic) |
|---|---|---|---|
| Sees | "Satisfaction −12%" | "Customers mention waits" | 16 long-wait complaints, clustered 12:45–13:45 |
| Explains | — | Summarizes text | Mix shift + surge hit the grill queue; staffing *not* the cause (evidence cited) |
| Decides | — | — | Move 1 staff assemble → grill (−67% grill waits in simulation) |
| Acts | — | — | Approval-gated recovery per complaint + staged kitchen change |
| Adapts | — | — | Replans when the fryer goes offline |
| Verifies | — | — | Simulates original vs revised plan *before* lunch; records every resolution |

The thesis in one line: **feedback → order records → operations → service
recovery → verification, in one workflow** — investigate *why*, determine
the action, coordinate the response, verify it worked. A dashboard reports;
a chatbot summarizes; an agent investigates, decides through approval
gates, adapts to new constraints, and verifies before the next rush.

---

## Project scope, inputs, outputs, constraints, success criteria, and definition of done

**Scope.** A deterministic, offline restaurant-ops agent demo: six steps
(categorize → investigate → root-cause → recover → coordinate → verify)
plus the fryer-offline twist, an agent-vs-baseline evaluation on 7
metrics, and a loyalty follow-up section — all exiting 0.

**Inputs (all synthetic).**

- 207 lunch orders (12:00–14:00 Friday) across 4 stations (GRILL/FRY/
  ASSEMBLE/BEVERAGE) from `build_world()`; per-bucket counts, station mix
  (today: grill 52% vs baseline 35%), capacity and staffing constants.
- 28 complaints: 16 long waits (clustered 12:45–13:45), 6 missing items, 4
  incorrect orders, 2 delivery delays.
- Pickup records, recovery authorization table, forecast inputs (history,
  day/time, weather, pre-orders).

**Outputs.**

- Root-cause verdict: demand surge + grill-heavy mix shift hit a fixed
  grill queue (mechanism-confirmed); understaffing NOT supported;
  inventory ruled out.
- Staged recommendation: move 1 staff assemble → grill (grill waits
  19.2 → 6.3 min in simulation) — pending manager approval.
- End-to-end recovery on one complaint (order TP-1094): lookup → verify
  pickup → policy check → draft → approve $5 coupon → record → verify;
  $20 unapproved refund BLOCKED.
- Revised plan under the fryer-offline constraint (pause fry sales,
  reassign 2 fry staff, fry prep capped at 0) with original-vs-revised
  simulation.
- 7-metric agent-vs-baseline scoreboard (all SIMULATED) + 3 scheduled
  loyalty follow-ups.

**Constraints.** Stdlib only, fully offline, no API keys. Fixed RNG seed,
fixed synthetic clock, sorted iteration → byte-identical output. Approval
gates on every staffing/customer-facing action (simulated taps, labeled as
such). Every metric labeled SYNTHETIC or SIMULATED.

**Success criteria.** Root cause correctly identifies the grill queue (not
staffing); the blocked-refund guardrail fires on screen; the revised plan
holds waits ~5 min with waste low and the 16-order outreach cost explicit;
evaluation table prints with mechanisms; `TEST-LOG.md` records 10/10
byte-identical runs.

**Definition of done.** All six steps + twist + evaluation + loyalty print
and exit 0; README carries all 10 checklist sections; `TEST-LOG.md` shows
the 10/10 determinism gate passing.

---

## Documented single-agent or multi-agent workflow

**Single-agent workflow** — one orchestrator + five capability tool groups.
Deliberately **not** five separate agents: fewer moving parts, one
decision-maker, one audit trail — and an easier story for students to
follow. (Five agents would need a sixth to coordinate them.)

```
                    ┌─────────────────────────────────┐
                    │        ORCHESTRATOR (1 agent)     │
                    │  plan → act → observe → replan  │
                    │  approval gates on every action │
                    └───────────────┬─────────────────┘
        ┌───────────────┬───────────┼───────────┬───────────────┐
        ▼               ▼           ▼           ▼               ▼
   (A) Experience  (B) Service  (C) Demand   (D) Root-cause  (E) Loyalty
     Intelligence   Recovery   & Kitchen      Analysis      & Experience
   ┌──────────┐   ┌────────┐  ┌─────────┐   ┌──────────┐   ┌──────────┐
   │categorize│   │lookup_ │  │forecast_│   │correlat- │   │unresolved│
   │_complaint│   │order   │  │demand   │   │ion_      │   │_followups │
   │concentra-│   │verify_ │  │check_   │   │analysis  │   │personal- │
   │tion      │   │pickup  │  │kitchen  │   │hypothes- │   │ization_  │
   │compare_  │   │check_  │  │check_   │   │is_tests  │   │context   │
   │volume    │   │policy  │  │ingred-  │   │estimate_ │   └──────────┘
   │station_  │   │draft_  │  │ients    │   │interven- │
   │waits     │   │response│  │recommend│   │tion      │
   │inspect_  │   │request_│  │_prep    │   │simulate_ │
   │handoff   │   │approval│  └─────────┘   │scenario  │
   └──────────┘   │record_ │                └──────────┘
                  │resol-  │
                  │ution   │
                  └────────┘
```

Every tool call is printed with its inputs and outputs, so the audience
watches the agent think. The queue model (`simulate_station`) is shared by
the data generator, the diagnosis, and the verify simulation — the story,
the root cause, and the numbers can't disagree with each other.

**The five capabilities:**

- **(A) Customer Experience Intelligence** — categorize complaints (long
  waits, missing items, incorrect orders, delivery delays), then *choose*
  which operational data to inspect based on the patterns found. Missing
  items clustered in the surge window → inspect order complexity/volume
  and the expedite-handoff process (not a pre-canned report).
- **(B) Personalized Service Recovery** — retrieve the order by reference,
  check timestamps/status, verify against pickup records (never assume
  delivered), check the authorized recovery policies, draft the response,
  request employee approval for anything requiring it, record and verify
  the resolution. **Never** issues refunds/compensation outside
  authorization rules — the demo shows the guardrail blocking a $20
  unapproved refund.
- **(C) Demand & Kitchen Coordination** — forecast near-term demand from
  history, day/time, weather, and incoming orders; check kitchen workload,
  ingredient availability, and bottlenecks; recommend staffing/prep
  adjustments **subject to manager approval**; prep to forecast + buffer,
  never blind over-prep (waste is a scored metric); revise the plan when
  conditions change (the fryer twist).
- **(D) Root-Cause Analysis** — the priority feature. Repeated long waits
  → investigate operational records → propose explanations with
  correlation and causation **explicitly separated**. The demo's signature
  moment: naive correlation has the *wrong sign* (r = −0.43) because queues
  lag arrivals; the causal claim rests on mechanism (45 minutes of
  arrivals > capacity, backlog curve tracking waits), never on r alone.
  Staffing is not blamed without evidence. Intervention effects are
  estimated via the same historical/simulation model before anything is
  recommended.
- **(E) Loyalty & Experience Improvement** — follow up on unresolved
  issues (3 complaints needing the customer's help get one scheduled
  follow-up each); personalization around **service preferences and the
  current problem only** (stated SMS preference, low-sodium note) — no
  inferred sensitive characteristics, no unwanted messages.

---

## Working prototype evidence, source code, and setup instructions

### Setup (MacBook) — live web UI (recommended for presenting)

You need nothing but Python 3, which ships with macOS.

```bash
cd ~/workspace/agentic-ai-workshop/guestfirst-ai
python3 app.py
```

The server prints `Open in Chrome: http://localhost:8008`. Open that URL in
Chrome and click **"Run live demo"** — the page calls `GET /api/run`, which
runs the real `demo.py` on your machine (via subprocess, never modified),
then renders the orchestrator's **plan** (highlighted at the top), the full
styled **agent trace** (the 6 steps, every `[tool]` call, approval gates,
the fryer twist), and a **key-results panel** (correlation sign-flip, the
recommended fix, the blocked refund, the replan, and the 7-metric
agent-vs-baseline scoreboard).

That's it. Fully offline — no API keys, no network, no installs (stdlib
only; see `requirements.txt`). If port 8008 is already in use, the server
exits with a clear error telling you to stop the other copy first.

### Terminal fallback

```bash
python3 demo.py
```

Same demo, printed in the terminal. Completes in well under a second. Output
is byte-identical on every run (fixed RNG seed, fixed synthetic clock,
sorted iteration) — verified 10/10 in `TEST-LOG.md`.

### What you'll see

| Printed section | What it teaches |
|---|---|
| The plan | The orchestrator decomposes the goal into 6 steps before acting — planning, not prompting |
| Steps 1–2 | Capability (A): categorize, then let the *pattern* choose which operational data to inspect |
| Step 3 | Capability (D): correlation ≠ causation, demonstrated with a real sign-flip, not a slogan |
| Approval gates | Nothing staffing- or customer-facing executes without a (simulated) human tap |
| Step 4 | Capability (B): lookup → verify → policy check → draft → approve → record → verify; the blocked-refund guardrail |
| Step 5 | Capability (C): forecast from history/day/time/weather/pre-orders; waste-aware prep levels |
| The twist | Replanning under a new constraint — the difference between a script and an agent |
| Step 6 | Verify-by-simulation: original vs revised plan compared *before* lunch |
| Evaluation | Agent vs baseline on 7 metrics, every number labeled SIMULATED with its mechanism |
| Loyalty | Capability (E): follow-ups + personalization with explicit anti-profiling guardrails |
| Closing | Why an agent, not a dashboard or chatbot + honesty notes |

### Files

- `app.py` — localhost web UI (entry point: `python3 app.py`, then open
  http://localhost:8008 in Chrome; `GET /` serves the page, `GET /api/run`
  runs `demo.py` via subprocess — stdlib only)
- `demo.py` — the whole demo (entry point: `python3 demo.py`)
- `requirements.txt` — stdlib-only note
- `TEST-LOG.md` — 10 consecutive runs: exit codes + output hashes; plus the
  12/12 web UI test log for `app.py`
- `RUBRIC.md` — honest self-score vs the hackathon judging rubric

### Speaker notes (6-minute walkthrough)

1. **Hook (30s):** Read the manager's question aloud. "A dashboard answers
   with a chart. A chatbot answers with a summary. Watch what an *agent*
   does with the same question."
2. **Investigate (1m):** Walk steps 1–2. Land the capability-A mantra: *"the
   pattern chooses the inspection."* Point at the grill number: 19.2 min vs
   2–5 everywhere else — one workflow, not "the kitchen."
3. **Root cause (1m30s):** This is the centerpiece. Read the two r values:
   "−0.43 — *negative*. If you stopped at correlation, you'd conclude grill
   orders *reduce* waits. The sign flips with a 30-minute lag — and even
   then, the agent doesn't trust r. It tests the mechanism." Then read the
   staffing verdict: "a constant cannot explain a change — the agent
   refuses to blame staffing without evidence." Ask the room: *"How many
   dashboards blame staffing by default?"*
4. **Recover (45s):** "It looked up the order, checked the pickup record —
   *verified, not assumed* — checked the policy table, drafted, and asked
   for approval." Then the blocked $20 refund: "the guardrail is the
   feature."
5. **Twist (1m):** "The fryer dies. A script would keep executing the old
   plan. Watch the replan." Read the verify table: waits hold, waste holds,
   and the cost — 16 fry orders — is explicit *before* lunch.
6. **Scoreboard + honesty (45s):** The 7-metric table, then read aloud:
   "every number is SIMULATED, from the demo's own models — it shows the
   mechanism, not a field trial." Close with the Chick-fil-A honesty line
   and: "Run it ten times — see TEST-LOG.md. Byte-identical."

Anticipated questions:

- *"Isn't the correlation sign-flip contrived?"* — No: it's computed from
  the demo's own queue model, and it's the honest behavior of lagged
  systems. The point is the agent's response: distrust r, test mechanism.
- *"Would this work with real data?"* — The shape transfers (see section
  10's table); the queue model would be fit to station timers, approvals
  become a real console queue.
- *"Why one orchestrator instead of five agents?"* — One decision-maker,
  one audit trail, and the capabilities share state (the complaint, the
  order, the forecast). Five agents would need a sixth to coordinate them.
- *"What if the agent's recommendation is wrong?"* — That's what the verify
  simulation and approval gates are for — and the README's honest-gap notes
  in RUBRIC.md say what a student team should add next (confidence
  intervals, real human taps).

---

## Functional and end-to-end testing, realistic scenarios, failure cases, reliability, and human oversight

**Realistic scenarios (end to end).** The Friday-lunch rush: 28 complaints
→ pattern-chosen inspection → mechanism-tested root cause → staged
staffing fix → end-to-end recovery on TP-1094 → tomorrow's forecast →
fryer-offline twist → replan → original-vs-revised verify simulation →
7-metric scoreboard → loyalty follow-ups.

**Failure cases the demo handles** (all from `demo.py` behavior):

- **Order status assumed delivered.** The agent *verifies* TP-1094 against
  pickup records (not picked up — still in the kitchen) and the draft
  response says so explicitly. `t_verify_pickup` returns the record or
  `None`; the workflow never assumes.
- **Unauthorized refund.** `issue_refund(order, $20, approval="none")` →
  **BLOCKED** by the policy guardrail: refunds need manager approval +
  duty-manager code. Escalated to a human. The agent NEVER issues
  compensation outside the authorization table.
- **Station goes offline.** `t_station_waits` skips stations with zero
  capacity (`if mix[s] <= 0 or capacities[s] <= 0: continue`) — the fryer
  simply drops out of the simulation instead of dividing by zero.
- **Complaint needs customer input.** Missing-item complaints needing a
  bag photo get one scheduled follow-up each (tomorrow 10:00 AM) — the
  agent does not guess; it schedules.
- **Blame without evidence.** Staffing never varied and matches baseline,
  so the agent explicitly does NOT claim understaffing caused the delays —
  "a constant cannot explain a change." Inventory: zero stockouts → ruled
  out.

**Reliability gate.** `TEST-LOG.md` records 10 consecutive runs of
`python3 demo.py` — exit codes + SHA-256 of full output — with the result
**10/10 PASSED, byte-identical output on every run**.

**Human oversight.** Approval gates on everything staffing- or
customer-facing: staffing changes, coupons, refunds, fry-menu pauses, and
customer outreach are staged, never executed, until a (simulated) human
tap. In production those taps become a real ops-console queue — the demo
labels every simulated tap as such.

---

## Focus, feasibility, and avoidance of unnecessary complexity

One orchestrator, five capability tool groups, one shared queue model —
stdlib only. Deliberately *not* built:

- **No separate agents.** One decision-maker, one audit trail; five agents
  would need a sixth to coordinate them.
- **No real forecast model.** `t_forecast_demand` is history × day-factor ×
  weather + pre-orders — transparent arithmetic, not a black box.
- **No live data feeds.** The synthetic world is generated in-code; the
  queue model is shared by the generator, the diagnosis, and the verify
  simulation so they can't disagree.
- **No hidden trade-offs.** The staffing move's cost (assemble waits rise
  slightly) and the revised plan's cost (16 fry orders need outreach) are
  printed, not buried.

Feasibility: ~820 lines a student can read end to end — and the shape
transfers to real data (queue model fit to station timers, approvals as a
real console queue) without changing the agent's structure.

---

## Interdisciplinary team roles and division of labor

| Role | Owns in this demo | Concrete component |
|---|---|---|
| **Domain researcher** | Restaurant-ops domain and causal discipline | The shared queue model (`simulate_station`), the correlation-vs-causation separation (r sign-flip + mechanism test), the no-blame-without-evidence rule, waste-aware prep policy |
| **Agent engineer** | Orchestrator, capability tools, and approval gates | The 6-step plan → act → observe → replan loop, the five capability tool groups, `t_request_approval` gates, the fryer-twist replan logic |
| **Data engineer** | The synthetic world and forecast inputs | `build_world` (207 orders, 28 complaints, pickup records), `t_forecast_demand` inputs, the station capacity/staffing constants, the real-data swap table in section 10 |
| **UX / storyteller** | The manager's-question narrative | Speaker notes (hook → investigate → root cause → recover → twist → scoreboard), the capability mantras ("the pattern chooses the inspection"), the Chick-fil-A honesty beat |
| **QA** | Determinism gate and the 7-metric scoreboard | `TEST-LOG.md` 10/10 byte-identical gate, the agent-vs-baseline evaluation with per-metric mechanisms, the blocked-refund guardrail demonstration |

---

## Limitations, risks, and responsible AI (ethics, privacy, security, safety)

**Responsible AI & guardrails (in the demo, not just the README):**

- **Approval gates:** staffing changes, coupons, refunds, fry-menu pauses,
  and customer outreach are staged, never executed, until a (simulated)
  human tap.
- **Authorization table:** apology + status update is auto-approved; a $5
  coupon needs manager approval; refunds need manager + duty-manager code;
  anything else is **blocked and escalated** — demonstrated live.
- **No blame without evidence:** the agent refuses to claim staffing caused
  delays when staffing never varied. Correlation ≠ causation is a printed
  analysis, not a disclaimer.
- **No intrusive profiling:** personalization uses only stated service
  preferences + the current problem. No inferred sensitive
  characteristics, no unsolicited messages.
- **Honest numbers:** every metric is labeled SYNTHETIC or SIMULATED with
  the mechanism that produced it. The evaluation table says what would
  change the result (it's a model comparison, not a field trial).

**Chick-fil-A: inspiration, honestly cited.** Chick-fil-A has publicly
described operational initiatives that inspired this demo's *problem
framing* — for example, geofenced mobile ordering that times food prep to
the customer's arrival, drive-thru work that cut waits by a minute or two,
pickup-time estimates that account for order complexity, and forecasting
prep needs from demand patterns. **Honesty rule, stated plainly:** these
public descriptions are cited as **INSPIRATION ONLY**. They do **not**
establish that Chick-fil-A uses this system, anything like this system, or
any AI agent at all. GuestFirst AI is a classroom demo about a fictional
chain; any resemblance to a real company's internal tooling is not claimed
and should not be inferred. If you present this demo, say that sentence
out loud.

**Data honesty — what's synthetic vs what would be real:**

| In the demo | In a real deployment |
|---|---|
| 207 synthetic lunch orders, fixed seed | POS/order feed, live |
| 28 synthetic complaints | Feedback inbox, app reviews, kiosk ratings |
| Queue-model waits (one shared model) | Kitchen display + timer data per station |
| Simulated manager taps | Real approval queue in the ops console |
| SIMULATED evaluation metrics | A/B measurement across locations/weeks |

---

## Practical value, adoption path, and measurable outcomes

**Practical value.** When complaints spike, the manager gets the *why*
(mechanism-tested root cause), the *what* (the fix, sized by simulation
before it's tried — grill waits 19.2 → 6.3 min), and the *proof* (original
vs revised plan simulated before lunch) — plus per-complaint recovery
with guardrails and loyalty follow-ups that don't profile.

**Adoption path.** To point this at real data, replace `build_world()`
with loaders for the order feed and complaint inbox; the orchestrator,
tools, approval gates, and verify loop don't change shape — only their
data sources do (see the table in section 9). Then: fit the queue model to
station timers, turn simulated taps into a real ops-console approval
queue, and add confidence intervals + real human taps per RUBRIC.md's
honest-gap notes.

**Measurable outcomes.** Today: byte-identical determinism (10/10) and the
7-metric agent-vs-baseline scoreboard — avg wait, order accuracy,
complaint resolution time, repeat complaint rate, forecast accuracy, food
waste, service recovery completion — each with its mechanism stated. In
production: the same seven, measured A/B across locations and weeks.

---

*Built for the Agentic AI Workshop · Demo 8 of 8*
