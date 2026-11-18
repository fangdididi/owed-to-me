---
name: owed-to-me
description: Worker-side money check before asking an employer for pay. Builds a case card, secures evidence before access disappears, turns time logs, leave and separation into money lines with a visible formula, grades each line by its weakest proof (HARD/FIRM/THIN), runs the claim clock, picks a route (ASK, COMPLAIN, MEDIATE, ARBITRATE, SETTLE) and outputs a linted claim sheet plus a calm written request. Use when someone says they were underpaid, worked unpaid overtime, has untaken leave, is being laid off or pushed out, or asks "how much am I owed" or "is it worth claiming".
---

# owed-to-me

**English** | [中文](SKILL.zh-CN.md)

## What this is

A careful, numbers-first way to answer one question for a worker: **what money am I actually owed, how sure can I be, and by when must I act?**

People usually arrive with a feeling ("they owe me for all those weekends") and leave with either nothing or an inflated number that falls apart the first time someone asks "show me". This skill sits in between. Every amount becomes a *money line* with a formula anyone can recompute, a list of proof, an honest proof grade, a deadline and a route. The result is a claim sheet split into SOLID, ARGUABLE and LONGSHOT money, so the worker knows the floor they should not go below and the extras they might trade away.

It is not legal advice and does not replace a lawyer, legal aid or the labour authority. It makes the worker's first conversation with any of them faster and much better prepared.

## When to use it

- "My company didn't pay overtime / weekend work / holiday shifts."
- "I'm leaving or being let go - what should I get?"
- "I never took my annual leave this year."
- "They never gave me a written contract."
- "Is it worth going to arbitration for this?"
- Before signing any separation agreement, resignation letter or settlement.

Do **not** use it to plan anything unlawful (taking company secrets, fabricating records, threats).

## Step 0 - Stop first if any of this is true

- Someone is hurt, in danger, threatened or held: safety and emergency services first.
- The worker is in crisis or mentions self-harm: point to local crisis support before anything else.
- A case is already filed or a ruling has arrived: say this skill only gives general structure and they need legal aid or a lawyer for the live case.
- They are about to sign something today: tell them it is normal to ask for a day to read it, and that signing a "voluntary resignation" or "no further claims" line can erase money lines.

## Step 1 - Case card

Write `case.json` → `card` with: employer, jurisdiction (rule pack), status (still employed / leaving / left, and *who* ended it and *why* as stated in writing), role, start and end dates, 12-month average monthly pay, and the worker's goal (fast money, keep a reference, principle, all of it). The goal decides the route later.

Pick the rule pack: `rules/cn.json` for mainland China enterprise employees, or copy `rules/blank.json` and fill every value **from an official text you actually read**. Never fill a rule from memory. A null value makes the script stop on purpose.

## Step 2 - Grab before it's gone

List every piece of proof in `evidence` with `id`, `what`, `holder`, `grade`, and `at_risk` if access can vanish (work chat removal, HR system login closing at exit, email account shutdown).

Grades:
- **HARD** - issued or kept by the employer or a third party: contract, payslips, bank wage transfers, attendance/badge exports, termination notice, social-insurance record.
- **FIRM** - made at the time and tied to the employer: manager messages assigning work, emails sent at 23:00, tickets with timestamps, photos of the rota.
- **THIN** - the worker's own later notes, memory, a colleague who "will probably confirm".

Secure at-risk items first, lawfully: export or photograph what you are entitled to see, forward your own payslips to a personal address if policy allows, write down dates while memory is fresh. Never copy confidential business data you have no right to; that turns a claimant into a defendant. Mark `secured: true` when done.

## Step 3 - Turn feelings into money lines

Each line in `lines` has: `id`, `type` (WAGE_GAP, OVERTIME, LEAVE, NO_CONTRACT, SEVERANCE, NOTICE_MONTH, UNLAWFUL_2N, EXPENSE, OTHER), `amount`, `formula`, `evidence` (ids), optional claimed `grade`, `event_date` (when the clock starts) and `route`.

Use the helper for the arithmetic, never mental maths:

```bash
python3 scripts/owed.py hours log.csv --rules rules/cn.json --monthly 12000 [--paid 800]
python3 scripts/owed.py leave --rules rules/cn.json --monthly 12000 --career-years 6 --taken 1 --days-employed 304
python3 scripts/owed.py severance --rules rules/cn.json --start 2022-03-14 --end 2026-10-31 --monthly-avg 12000 --route N [--local-avg 9000]
```

The time log CSV columns are `date,start,end,break_min,day_type(work|rest|holiday),comp_off,evidence`. Split overtime into separate lines by proof grade (the `hours` output shows the amount per grade), so strong hours are not dragged down by weak ones.

Rules of honesty:
- A line's grade is the **weakest essential proof**, not the strongest. The linter rejects a line that claims more.
- Don't stack lines that replace each other (2N already replaces N and the notice month).
- Use the 12-month average including bonuses and allowances only if the rule pack says they count; write which items you included in the formula.

## Step 4 - Run the clock

```bash
python3 scripts/owed.py clock --rules rules/cn.json --event 2026-10-31
```

States: OPEN (> 90 days), SOON (≤ 90), URGENT (≤ 30), EXPIRED. Each line gets its own last day in the sheet. EXPIRED is not automatically the end - ask legal aid whether the window was paused or restarted - but it must be said out loud.

## Step 5 - Choose a route per line

| route | good for | money | time | stamina |
|---|---|---|---|---|
| ASK | clear numbers, ongoing relationship, reference matters | none | days | low |
| COMPLAIN | unpaid wages, missing contributions, many workers affected (labour inspection) | none | weeks | low |
| MEDIATE | both sides want it over, numbers mostly agreed | none | weeks | medium |
| ARBITRATE | employer refuses, money is SOLID or ARGUABLE, deadline approaching | low | months | high |
| SETTLE | trade LONGSHOT money for speed or a clean exit | none | days | low |

Match the route to the goal in the case card. Start with the cheapest route that can work and keep the stronger one as the next step, not as a threat.

## Step 6 - Lint and print the claim sheet

```bash
python3 scripts/owed.py sheet case.json --rules rules/cn.json
```

Verdict **READY** or **FIX** (exit code 1). Codes:

| code | meaning | blocks? |
|---|---|---|
| L01 | no formula | yes |
| L02 | no evidence / unknown evidence id | yes |
| L03 | claimed grade stronger than weakest proof | yes |
| L04 | no event date, so no deadline | no |
| L05 | window looks closed | no |
| L06 | 30 days or less left | no |
| L07 | 2N stacked with N or notice month | no |
| L08 | amount not positive | yes |
| L09 | rule pack never checked | no |
| L10 | case card incomplete | yes |
| L11 | unknown line type | yes |
| L12 | no route | no |
| L13 | at-risk evidence not yet secured | no |

The sheet totals SOLID / ARGUABLE / LONGSHOT and names the **settlement floor** = SOLID total. Below that floor the worker is giving away money they can prove.

## Step 7 - Write the request

A short written request (email or letter, keep a copy) with: who you are and your dates; each line with amount and the formula in one sentence; the proof you hold (not the proof you lack); a reasonable reply-by date; and a neutral last line ("If we can't settle this directly I will use the formal channel available to me"). No insults, no threats, no exaggeration - the request may be read later by an arbitrator.

## Example (short)

QA engineer, 4 years 7 months, let go citing restructuring, 12,000/month average. Helper output: severance N = 5 months → 60,000 (HARD); notice month 12,000 (HARD, only if no 30-day notice); 3 unused leave days → 3,310.34 (HARD); weekday + rest-day overtime 1,534.48 (FIRM, chat messages); holiday shift 827.59 (THIN, own notes). Sheet: SOLID 75,310.34 / ARGUABLE 1,534.48 / LONGSHOT 827.59; L13 warns the chat proof isn't saved yet. Route: ASK for the SOLID lines with a 7-day reply date, keep ARBITRATE ready; offer to drop the holiday line in exchange for a fast payment. Full files in `examples/`.

## Tips

- Numbers beat adjectives. "1,534.48 = 7.5 weekday h × 68.97 × 1.5 + 5.5 rest-day h × 68.97 × 2" ends arguments that "a lot of overtime" starts.
- Write the event date for every line on day one; deadlines are the most common way people lose money they could prove.
- Re-run the sheet each time new proof arrives - a THIN line can become FIRM.
- Ask for the employer's own records (attendance, payroll) in writing; refusal to provide them can itself matter in some systems.
- Local numbers (minimum wage, local average wage, holiday calendar, special hour systems) differ by city - check them, don't assume.
- Free first help: in mainland China 12333 (HR & social security) and 12348 (public legal service); elsewhere, the labour inspectorate or legal aid office.
