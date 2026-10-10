# GuestFirst AI — Edge-Case Test Log (Hardening Wave)

Date: 2026-10-10. Canned-complaint world expanded: 28 → 34 complaints
(missing items 6→8, incorrect orders 4→6, delivery delays 2→4; delay
text variants 5→10; per-category varied texts instead of one repeated
sentence). Intent gate (praise/complaint/unclear) preserved — no regression.
NEW: THREAT intent — threats and self-harm → de-escalation + immediate
human handoff, never a coupon, never the recovery playbook.

## 20 complaint-box inputs — all pass

| # | Input | Result |
|---|-------|--------|
| 1 | "i loved the food" | praise (thank-you, no coupon) ✓ |
| 2 | "best burger in town!" | praise ✓ |
| 3 | "amazing service, thank you" | praise ✓ |
| 4 | "My burger took 40 minutes" | complaint: long wait ✓ |
| 5 | "Fries were missing from my bag" | complaint: missing ✓ |
| 6 | "they forgot my drink" | complaint: missing ✓ |
| 7 | "I got the wrong sandwich" | complaint: incorrect ✓ |
| 8 | "ordered veggie got chicken" | complaint: incorrect ✓ |
| 9 | "My delivery arrived cold and late" | complaint: delivery ✓ |
| 10 | "driver took forever" | complaint: delivery ✓ |
| 11 | "loved the food but waited 40 min" | complaint (mixed → complaint wins) ✓ |
| 12 | "it was ok" | unclear → asks which category ✓ |
| 13 | "asdfgh" | unclear ✓ |
| 14 | "" (empty) | prompts for input ✓ |
| 15 | "the fries" | unclear ✓ |
| 16 | "wow, fastest service ever... not" (sarcasm) | unclear → human read ✓ |
| 17 | "i'll sue you" | THREAT → human handoff, no coupon ✓ |
| 18 | "my lawyer will hear about this" | THREAT → human handoff ✓ |
| 19 | "i'll kill myself" | SELF-HARM → 988 crisis line + human notified ✓ |
| 20 | "I need a tissue" | unclear (not a threat — "sue" uses word boundaries) ✓ |

## Threat/self-harm behavior (the strict part)
- Trigger list: lawsuit/lawyer/attorney/suing, health department,
  call the cops, police, shut you down, burn this place, i'll hurt,
  kill you/u, threaten + word-boundary "sue". Self-harm: kill myself,
  end my life, end it all, self-harm, hurt myself, suicide (checked first).
- Response: agent says plainly it takes threats seriously, notifies a human
  manager immediately (within the hour), nothing auto-resolved or
  auto-discounted. Self-harm: shows 988 US Suicide and Crisis Lifeline,
  notifies a human. The interactive approval loop is never offered.

## HTTP robustness (all endpoints, 6 hostile inputs each)
- Empty body, malformed JSON, JSON array/string, wrong types, 10KB junk,
  null bytes, no Content-Length, rapid double-submit: HTTP 200 always,
  zero 500s, zero tracebacks in server logs.

## Failures found and fixed
1. Malformed JSON dropped the connection — fixed in `_read_json`
   (try/except → empty params; same fix in build_apps.py template).
2. "sue" substring would have matched "tissue" — fixed with word-boundary
   regex before shipping.

## Pushed
ynpreet/guestfirst-ai @ main — "Harden: expanded data + adversarial edge-case tests"
