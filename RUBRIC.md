# RUBRIC.md — Self-score vs. the PEAAII Hackathon Judging Rubric

Scored 1–5 per criterion against `~/workspace/peaii-hackathon/judging-rubric.md`, with concrete evidence, one honest gap per criterion, and how a student could close it.

| # | Criterion (weight) | Score | Points |
|---|---|---|---|
| 1 | Problem Definition & Real-World Impact (25) | 4/5 | 20 |
| 2 | Meaningful Agentic AI Behavior (20) | 5/5 | 20 |
| 3 | Working Prototype (15) | 5/5 | 15 |
| 4 | Innovation & Creativity (15) | 4/5 | 12 |
| 5 | Presentation & Communication (15) | 5/5 | 15 |
| 6 | Responsible AI & Feasibility (10) | 5/5 | 10 |
| | **TOTAL** | | **92/100** |

---

## 1. Problem Definition & Real-World Impact — 4/5 (20 pts)

**Evidence:** A specific user (a TastePoint location manager) with a concrete,
high-stakes question ("why are customers complaining about long wait times
today, and what should we do?") — not "everyone." The pain is genuine and
operational: lunch-rush complaints, a grill queue bottleneck, food waste from
over-prep, and a fryer outage. The demo answers with named orders
(TP-1094), quantified waits (19.2 → 6.3 min), and a 7-metric scoreboard.

**Honest gap:** The framing claims "thousands of customers daily, multiple
locations," but the demo only ever shows one location's lunch shift (207
orders). The multi-location story is asserted, not demonstrated.

**Close it:** Add a second location's lunch to the synthetic world and have
the orchestrator compare ("Downtown's grill queue vs Riverside's — same
surge, different bottleneck"), proving the agent generalizes across sites.

## 2. Meaningful Agentic AI Behavior — 5/5 (20 pts)

**Evidence:** The agentic loop is the demo and it's *printed*: the
orchestrator publishes a 6-step plan before acting, makes 20+ tool calls with
visible inputs/outputs, lets complaint patterns *choose* which operational
data to inspect (capability A), replans from scratch when the fryer goes
offline (the twist), stages every consequential action behind approval gates,
and closes the loop with verify-by-simulation. A chatbot could not do this —
it requires planning, tool use, state, replanning, and gated autonomous
action. The "why an agent, not a dashboard or chatbot" section makes the case
explicitly.

**Honest gap:** The tools are in-process Python functions and the manager's
approval taps are simulated — a hard-nosed judge could call the autonomy
staged rather than real.

**Close it:** Put one real boundary in: run the approval tap through an actual
human input (`input("approve? y/n")`) in an `--interactive` mode, so the
audience sees the agent genuinely wait on a human.

## 3. Working Prototype — 5/5 (15 pts)

**Evidence:** `python3 demo.py` is the entire demo — stdlib only, fully
offline, completes in well under a second, and TEST-LOG.md proves 10/10
byte-identical runs with exit code 0. The queue model is shared by the data
generator, the diagnosis, and the simulation, so the story and the numbers
can't disagree.

**Honest gap:** One fixed scenario, no interactive mode — a student presenting
live can't ask "what if the surge were 60%?" and get an answer.

**Close it:** Add CLI flags (`--surge 1.6`, `--fryer-down`) that re-parameterize
the synthetic world deterministically — same seed logic, new what-if, still
reproducible.

## 4. Innovation & Creativity — 4/5 (12 pts)

**Evidence:** Three design choices stand out: (1) the correlation sign-flip
(r = −0.43 naive → +0.50 lagged) used as a *live* root-cause lesson instead of
a slogan; (2) verify-by-simulation comparing original vs revised plans
*before* lunch service; (3) one orchestrator + five capability tool-groups
instead of a multi-agent swarm — a deliberate simplicity with one audit trail.
Service-recovery workflows exist in industry, so this is creative composition
rather than invention from nothing.

**Honest gap:** The scenario beats are fixed — the twist always fires at the
same moment with the same fault. A judge probing "is it really replanning?"
gets only one demonstration.

**Close it:** Randomize (seeded) which station fails and when, and print the
replan diff each time — proving the revision logic is general, not scripted
for the fryer.

## 5. Presentation & Communication — 5/5 (15 pts)

**Evidence:** The README carries the full non-technical story: a 30-second
setup, a what-you'll-see table, an ASCII architecture diagram, a 6-minute
speaker-notes script with anticipated questions, MacBook run steps assuming
zero setup, and a say-it-out-loud Chick-fil-A honesty beat. The demo's own
output narrates itself in plain English ("we verify; we do NOT assume"),
with mechanisms attached to every number.

**Honest gap:** No visuals — it's a terminal demo, and a live room responds
to at least one picture.

**Close it:** Add one slide rendering the ASCII architecture as a real
diagram, plus a simple wait-curve chart (baseline vs original vs revised
plan) generated as a static SVG from the demo's own numbers — no new
dependencies.

## 6. Responsible AI & Feasibility — 5/5 (10 pts)

**Evidence:** Guardrails are *demonstrated*, not just documented: the
authorization table (auto-approved vs manager vs blocked), the live
blocked-$20-refund, approval gates on staffing/kitchen/customer actions, the
explicit refusal to blame staffing without evidence, anti-profiling rules for
personalization (stated preferences + current problem only), SIMULATED
labeling with mechanisms on every metric, and the Chick-fil-A honesty section
stating plainly what the inspiration does *not* establish. The README's data
honesty table shows exactly what would change to point this at real data.

**Honest gap:** The approvals are simulated taps and the simulation reports
point estimates with no uncertainty — a real manager should see confidence
("grill waits 5–8 min") before betting a lunch rush on it.

**Close it:** Have the verify simulation report ranges (run the queue model
over ±20% demand scenarios) and replace one simulated tap with a real human
confirmation, so the human-in-the-loop is load-bearing, not theatrical.
