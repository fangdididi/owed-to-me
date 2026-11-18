# owed-to-me

**English** | [中文](README.zh-CN.md)

> Know what your employer owes you, how sure you can be, and the last day to act, before you ask for a single cent.

`owed-to-me` is an agent skill (Claude Code, Codex, Cursor and any agent that reads `SKILL.md`) for the worker's side of a pay dispute. It turns "they owe me for all those weekends" into a claim sheet where every amount has a formula, proof, an honest proof grade, a deadline and a route, and tells you the settlement floor you should not go below.

It is a preparation tool, not legal advice.

## The problem it solves

- People under-claim because they don't know what exists (unused leave, notice month, double wage for no contract).
- People over-claim with numbers they can't prove, and lose credibility on the lines they *could* prove.
- People lose provable money to deadlines and to evidence that disappears the day their work accounts close.
- People sign "voluntary resignation / no further claims" papers before doing the maths.

## Features

- **Case card** - one place for dates, pay, who ended the job and why, and what the worker really wants.
- **Grab-before-gone evidence inventory** - HARD / FIRM / THIN grades, `at_risk` flags, lawful-preservation guidance.
- **Money lines** - WAGE_GAP, OVERTIME, LEAVE, NO_CONTRACT, SEVERANCE, NOTICE_MONTH, UNLAWFUL_2N, EXPENSE, OTHER; each graded by its *weakest* essential proof.
- **Calculator** (`scripts/owed.py`) - overtime from a time log (overnight shifts, comp-off days, per-grade split), pro-rated annual leave, N / N+1 / 2N separation pay with high-earner cap, claim clock.
- **Rule packs** - `rules/cn.json` (mainland China, with the legal source of each number) and `rules/blank.json` for any other jurisdiction; empty values stop the maths instead of guessing.
- **Route table** - ASK, COMPLAIN, MEDIATE, ARBITRATE, SETTLE with money / time / stamina cost.
- **Linted claim sheet** - 13 checks, READY / FIX verdict, SOLID / ARGUABLE / LONGSHOT totals and the settlement floor.
- **Calm written request** - structure for an email or letter an arbitrator could read later.
- Full English and Chinese versions; Python standard library only; 15 tests.

## Install

```bash
git clone https://github.com/fangdididi/owed-to-me.git
```

| agent | where to put it |
|---|---|
| Claude Code | `~/.claude/skills/owed-to-me/` (or `.claude/skills/` in a project) |
| Codex | `~/.codex/skills/owed-to-me/` or reference `SKILL.md` from `AGENTS.md` |
| Cursor | `.cursor/skills/owed-to-me/` or add `SKILL.md` as a project rule |
| any other agent | point it at `SKILL.md` (English) or `SKILL.zh-CN.md` (Chinese) |

Then ask, for example: *"I was laid off after 4 years 7 months, average 12,000 a month, and I have weekend work in chat messages. What am I owed?"*

## Use the calculator directly

```bash
python3 scripts/owed.py hours examples/hours.csv --rules rules/cn.json --monthly 12000
python3 scripts/owed.py leave --rules rules/cn.json --monthly 12000 --career-years 6 --taken 1 --days-employed 304
python3 scripts/owed.py severance --rules rules/cn.json --start 2022-03-14 --end 2026-10-31 --monthly-avg 12000 --route N
python3 scripts/owed.py clock --rules rules/cn.json --event 2026-10-31
python3 scripts/owed.py sheet examples/case.json --rules rules/cn.json
python3 -m unittest discover -s tests
```

## Example output

```
| id | type | amount | proof | tier | route | last day |
| M1 | OVERTIME | CNY 1534.48 | FIRM | ARGUABLE | ARBITRATE | 2027-10-31 (OPEN) |
| M2 | OVERTIME | CNY 827.59 | THIN | LONGSHOT | ARBITRATE | 2027-10-31 (OPEN) |
| M3 | LEAVE | CNY 3310.34 | HARD | SOLID | ASK | 2027-10-31 (OPEN) |
| M4 | SEVERANCE | CNY 60000.00 | HARD | SOLID | ASK | 2027-10-31 (OPEN) |
| M5 | NOTICE_MONTH | CNY 12000.00 | HARD | SOLID | ASK | 2027-10-31 (OPEN) |

settlement floor (SOLID only): CNY 75310.34
L13 evidence E4 may vanish (work chat account removal) - secure a copy first
```

(Fictional employer and numbers.)

## File structure

```
owed-to-me/
├── SKILL.md             # skill instructions (English)
├── SKILL.zh-CN.md       # skill instructions (Chinese)
├── README.md
├── README.zh-CN.md
├── LICENSE
├── rules/
│   ├── cn.json          # mainland China rule pack with legal sources
│   └── blank.json       # template for any other jurisdiction
├── scripts/
│   └── owed.py          # hours / leave / severance / clock / sheet
├── examples/
│   ├── hours.csv        # sample time log
│   └── case.json        # sample case: card, evidence, money lines
└── tests/
    └── test_owed.py     # 15 tests
```

## Important

Rules change and vary by city. Check every rule-pack value against the current official text before you rely on it, and talk to legal aid, the labour authority or a lawyer for a live case.

## License

MIT © fangdididi
