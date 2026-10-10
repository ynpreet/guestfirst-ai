# TEST-LOG.md — Determinism verification

**Date:** 2026-10-10
**Command:** `python3 demo.py` (10 consecutive runs, same machine, same session)
**Method:** each run's stdout+stderr captured to a file; recorded exit code and SHA-256 of full output.

| Run | Exit code | SHA-256 of output | Result |
|-----|-----------|-------------------|--------|
| 1 | 0 | `1580b6cbc3fd30ac9561981f8318f02806ecb3cb966ec762f3a09a5867ec3f84` | PASS |
| 2 | 0 | `1580b6cbc3fd30ac9561981f8318f02806ecb3cb966ec762f3a09a5867ec3f84` | PASS |
| 3 | 0 | `1580b6cbc3fd30ac9561981f8318f02806ecb3cb966ec762f3a09a5867ec3f84` | PASS |
| 4 | 0 | `1580b6cbc3fd30ac9561981f8318f02806ecb3cb966ec762f3a09a5867ec3f84` | PASS |
| 5 | 0 | `1580b6cbc3fd30ac9561981f8318f02806ecb3cb966ec762f3a09a5867ec3f84` | PASS |
| 6 | 0 | `1580b6cbc3fd30ac9561981f8318f02806ecb3cb966ec762f3a09a5867ec3f84` | PASS |
| 7 | 0 | `1580b6cbc3fd30ac9561981f8318f02806ecb3cb966ec762f3a09a5867ec3f84` | PASS |
| 8 | 0 | `1580b6cbc3fd30ac9561981f8318f02806ecb3cb966ec762f3a09a5867ec3f84` | PASS |
| 9 | 0 | `1580b6cbc3fd30ac9561981f8318f02806ecb3cb966ec762f3a09a5867ec3f84` | PASS |
| 10 | 0 | `1580b6cbc3fd30ac9561981f8318f02806ecb3cb966ec762f3a09a5867ec3f84` | PASS |

**Result: 10/10 PASS** — exit code 0 and byte-identical output on every run.

Determinism sources: one seeded RNG (`random.Random(20261010)`), a fixed
synthetic clock (13:05 — no wall-clock time anywhere), sorted iteration over
all mappings, and fixed station/bucket ordering. The flakiness that had to be
fixed during development: the first draft printed literal `%%` (format-string
bug), reported a negative Pearson r as "moderate" instead of teaching the
sign-flip, and divided by zero when the fryer went offline (fixed by routing
fry demand through an adjusted mix instead of simulating a zero-capacity
station).

---

# Web UI test log — `app.py` (localhost demo server)

**Date:** 2026-10-10
**Command:** `python3 app.py` (stdlib-only `http.server`, port 8008, bind 127.0.0.1)
**Method:** 12 rounds. Each round: (a) `python3 demo.py` → exit 0; (b) start
`app.py`, wait for the port, then `curl /` → HTTP 200 (page contains the
"Run live demo" button and title) and `curl /api/run` → HTTP 200 with
`{"ok": true, ...}` whose `output` contains all six stable markers
(`plan (capabilities in brackets)`, `Pearson r = -0.43`, `Pearson r = 0.50`,
`!!! TWIST -- 13:05`, `APPROVAL GATE`, `SYNTHETIC or SIMULATED`); then kill the
server by PID and confirm the port is free. Startup banner
(`Open in Chrome: http://localhost:8008`) and the port-in-use error path
(clear message + exit 1 when 8008 is taken) verified separately.

**Result: 12/12 PASS** — every round: demo exit 0, `GET /` 200, `GET /api/run`
200 with all markers present.

Flakiness found and fixed (all in `app.py` / the test harness, never in
`demo.py`):
- `socketserver.ThreadingTCPServer.allow_reuse_address` is `False` (unlike
  `http.server.ThreadingHTTPServer`), so rapid server restarts between rounds
  could trip on TIME_WAIT sockets. Fixed by setting `allow_reuse_address = True`
  before binding.
- The first test harness started the server via `setsid ... &` and killed `$!`,
  but `setsid` forks when it is the process-group leader, so `$!` was the wrong
  PID and the kill was a no-op — the next round's server then died with
  EADDRINUSE (2 of the first 12 rounds failed this way: `curl` → 000). Fixed by
  starting the server as a plain background job (no `setsid`), killing the real
  PID, and asserting the server process is alive before each check.
