#!/usr/bin/env python3
"""owed.py - worker-side money check: overtime, unused leave, severance,
claim clock and a linted claim sheet. Standard library only.

Commands
  hours     overtime owed from a time log CSV
  leave     unused annual leave payout
  severance N / N+1 / 2N separation pay
  clock     last safe day to file from an event date
  sheet     lint a case file and print a claim sheet (markdown)

Every number depends on a rule pack (rules/*.json). A null rule value
stops the calculation instead of guessing.
"""
import argparse, csv, datetime as dt, json, sys

GRADES = ["HARD", "FIRM", "THIN"]          # strongest -> weakest
TIER = {"HARD": "SOLID", "FIRM": "ARGUABLE", "THIN": "LONGSHOT"}
LINE_TYPES = {"WAGE_GAP", "OVERTIME", "LEAVE", "NO_CONTRACT", "SEVERANCE",
              "NOTICE_MONTH", "UNLAWFUL_2N", "EXPENSE", "OTHER"}


class RuleMissing(Exception):
    pass


def need(rules, *path):
    v = rules
    for p in path:
        v = v.get(p) if isinstance(v, dict) else None
        if v is None:
            raise RuleMissing("rule pack has no value for " + ".".join(path))
    return v


def load_rules(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def d(s):
    return dt.date.fromisoformat(s)


def weakest(grades):
    grades = [g for g in grades if g in GRADES]
    if not grades:
        return "THIN"
    return max(grades, key=GRADES.index)


# ---------------------------------------------------------------- hours
def shift_hours(start, end, break_min):
    t0 = dt.datetime.strptime(start, "%H:%M")
    t1 = dt.datetime.strptime(end, "%H:%M")
    if t1 <= t0:                       # crossed midnight
        t1 += dt.timedelta(days=1)
    h = (t1 - t0).total_seconds() / 3600 - float(break_min or 0) / 60
    return max(h, 0.0)


def overtime(rows, rules, monthly_wage, paid_already=0.0):
    std = need(rules, "standard_daily_hours")
    days = need(rules, "paid_days_per_month")
    mult = {k: need(rules, "overtime_multiplier", k) for k in ("work", "rest", "holiday")}
    comp_cancels = need(rules, "rest_day_comp_off_cancels_pay")
    hourly = monthly_wage / days / std
    out = {"hourly": round(hourly, 2), "hours": {"work": 0.0, "rest": 0.0, "holiday": 0.0},
           "by_grade": {g: 0.0 for g in GRADES}, "days": 0, "flags": []}
    for r in rows:
        kind = (r.get("day_type") or "work").strip().lower()
        if kind not in mult:
            raise ValueError("unknown day_type %r on %s" % (kind, r.get("date")))
        h = shift_hours(r["start"], r["end"], r.get("break_min", 0))
        if kind == "work":
            extra = max(h - std, 0.0)
        elif kind == "rest" and comp_cancels and (r.get("comp_off") or "").strip().lower() in ("yes", "y", "1", "true"):
            extra = 0.0
        else:
            extra = h
        if h > 16:
            out["flags"].append("%s: %.1f h in one shift - double-check the record" % (r["date"], h))
        out["hours"][kind] += extra
        g = (r.get("evidence") or "THIN").strip().upper()
        g = g if g in GRADES else "THIN"
        out["by_grade"][g] += extra * hourly * mult[kind]
        out["days"] += 1
    gross = sum(out["by_grade"].values())
    out["gross"] = round(gross, 2)
    out["paid_already"] = round(paid_already, 2)
    out["owed"] = round(max(gross - paid_already, 0.0), 2)
    out["hours"] = {k: round(v, 2) for k, v in out["hours"].items()}
    out["by_grade"] = {k: round(v, 2) for k, v in out["by_grade"].items()}
    out["formula"] = "sum(extra_hours x %.2f/h x multiplier[day_type]) - paid_already" % hourly
    return out


# ---------------------------------------------------------------- leave
def leave_days_entitled(rules, career_years, days_employed_this_year, year_days=365):
    tiers = need(rules, "leave_tiers")
    full = 0
    for min_years, days in tiers:
        if career_years >= min_years:
            full = days
    return int(full * days_employed_this_year / year_days)   # fractions dropped


def leave_payout(rules, monthly_wage, career_years, days_taken, days_employed_this_year, year_days=365):
    per_day = monthly_wage / need(rules, "paid_days_per_month")
    extra = need(rules, "leave_extra_multiplier")
    ent = leave_days_entitled(rules, career_years, days_employed_this_year, year_days)
    unused = max(ent - days_taken, 0)
    return {"entitled_days": ent, "taken": days_taken, "unused": unused,
            "daily_wage": round(per_day, 2), "owed": round(unused * per_day * extra, 2),
            "formula": "unused %d d x %.2f/d x %s" % (unused, per_day, extra)}


# ---------------------------------------------------------------- severance
def service_months(start, end):
    m = (end.year - start.year) * 12 + (end.month - start.month)
    if end.day < start.day:
        m -= 1
    return max(m, 0)


def severance(rules, start, end, monthly_avg, route="N", local_avg=None, last_month=None):
    half_below = need(rules, "severance_half_month_below_months")
    months = service_months(start, end)
    yrs, rem = divmod(months, 12)
    n = float(yrs)
    if rem >= half_below:
        n += 1
    elif rem > 0 or (months == 0 and end > start):
        n += 0.5
    base = monthly_avg
    capped = False
    if local_avg:
        cap_mult = need(rules, "severance_cap_multiple_of_local_avg")
        cap_years = need(rules, "severance_cap_years")
        if monthly_avg > cap_mult * local_avg:
            base = cap_mult * local_avg
            n = min(n, cap_years)
            capped = True
    amount = n * base
    route = route.upper()
    if route == "N+1":
        amount += last_month if last_month is not None else monthly_avg
    elif route == "2N":
        amount *= 2
    elif route != "N":
        raise ValueError("route must be N, N+1 or 2N")
    return {"service_months": months, "n": n, "base": round(base, 2), "capped": capped,
            "route": route, "owed": round(amount, 2),
            "formula": "%s with N=%s x base %.2f%s" % (route, n, base, " (high-earner cap)" if capped else "")}


# ---------------------------------------------------------------- clock
def clock(rules, event, today=None):
    days = need(rules, "claim_window_days")
    today = today or dt.date.today()
    last = event + dt.timedelta(days=days)
    left = (last - today).days
    state = "EXPIRED" if left < 0 else ("URGENT" if left <= 30 else ("SOON" if left <= 90 else "OPEN"))
    return {"event": event.isoformat(), "last_day": last.isoformat(), "days_left": left, "state": state}


# ---------------------------------------------------------------- sheet
def lint(case, rules, today=None):
    today = today or dt.date.today()
    issues = []
    card = case.get("card", {})
    for k in ("jurisdiction", "status", "employer"):
        if not card.get(k):
            issues.append(("L10", "case card missing '%s'" % k))
    if not rules.get("checked_on"):
        issues.append(("L09", "rule pack never checked against official text"))
    ev = {e["id"]: e for e in case.get("evidence", [])}
    types = set()
    for ln in case.get("lines", []):
        lid = ln.get("id", "?")
        t = ln.get("type")
        types.add(t)
        if t not in LINE_TYPES:
            issues.append(("L11", "%s: unknown type %r" % (lid, t)))
        if not ln.get("formula"):
            issues.append(("L01", "%s: no formula - nobody can check the number" % lid))
        refs = ln.get("evidence", [])
        if not refs:
            issues.append(("L02", "%s: no evidence attached" % lid))
        missing = [r for r in refs if r not in ev]
        if missing:
            issues.append(("L02", "%s: evidence ids not in inventory: %s" % (lid, ", ".join(missing))))
        real = weakest([ev[r].get("grade") for r in refs if r in ev]) if refs and not missing else "THIN"
        if ln.get("grade") and GRADES.index(ln["grade"]) < GRADES.index(real):
            issues.append(("L03", "%s: says %s but weakest essential proof is %s" % (lid, ln["grade"], real)))
        ln["_grade"] = real
        if not ln.get("event_date"):
            issues.append(("L04", "%s: no event date, so no deadline" % lid))
        else:
            c = clock(rules, d(ln["event_date"]), today) if rules.get("claim_window_days") else None
            ln["_clock"] = c
            if c and c["state"] == "EXPIRED":
                issues.append(("L05", "%s: window looks closed (%s) - ask whether an exception applies" % (lid, c["last_day"])))
            elif c and c["state"] == "URGENT":
                issues.append(("L06", "%s: only %d days left (last day %s)" % (lid, c["days_left"], c["last_day"])))
        if not isinstance(ln.get("amount"), (int, float)) or ln["amount"] <= 0:
            issues.append(("L08", "%s: amount must be a positive number" % lid))
        if not ln.get("route"):
            issues.append(("L12", "%s: no route chosen" % lid))
    if "UNLAWFUL_2N" in types and ({"SEVERANCE", "NOTICE_MONTH"} & types):
        issues.append(("L07", "2N already replaces N and the notice month - keep one, not both"))
    for e in case.get("evidence", []):
        if e.get("at_risk") and not e.get("secured"):
            issues.append(("L13", "evidence %s may vanish (%s) - secure a copy first" % (e["id"], e["at_risk"])))
    return issues


def sheet(case, rules, today=None):
    issues = lint(case, rules, today)
    blocking = {"L01", "L02", "L03", "L08", "L10", "L11"}
    verdict = "FIX" if any(c in blocking for c, _ in issues) else "READY"
    cur = rules.get("currency", "")
    tiers = {"SOLID": 0.0, "ARGUABLE": 0.0, "LONGSHOT": 0.0}
    out = ["# Claim sheet - %s" % case.get("card", {}).get("employer", "?"), "",
           "Verdict: **%s**  |  rule pack: %s (checked %s)" % (verdict, rules.get("pack"), rules.get("checked_on") or "never"), "",
           "| id | type | amount | proof | tier | route | last day |", "|---|---|---:|---|---|---|---|"]
    for ln in case.get("lines", []):
        g = ln.get("_grade", "THIN")
        amt = ln.get("amount") if isinstance(ln.get("amount"), (int, float)) else 0
        tiers[TIER[g]] += amt
        c = ln.get("_clock") or {}
        out.append("| %s | %s | %s %.2f | %s | %s | %s | %s %s |" % (
            ln.get("id"), ln.get("type"), cur, amt, g, TIER[g], ln.get("route", "-"),
            c.get("last_day", "-"), "(%s)" % c["state"] if c else ""))
    out += ["", "| tier | total |", "|---|---:|"]
    for k, v in tiers.items():
        out.append("| %s | %s %.2f |" % (k, cur, v))
    out.append("| settlement floor (SOLID only) | %s %.2f |" % (cur, tiers["SOLID"]))
    out += ["", "## Lint"]
    out += ["- %s %s" % i for i in issues] or ["- clean"]
    return verdict, "\n".join(out), tiers, issues


# ---------------------------------------------------------------- cli
def main(argv=None):
    p = argparse.ArgumentParser(prog="owed.py")
    sub = p.add_subparsers(dest="cmd", required=True)
    h = sub.add_parser("hours"); h.add_argument("csv"); h.add_argument("--rules", required=True)
    h.add_argument("--monthly", type=float, required=True); h.add_argument("--paid", type=float, default=0.0)
    lv = sub.add_parser("leave"); lv.add_argument("--rules", required=True)
    lv.add_argument("--monthly", type=float, required=True); lv.add_argument("--career-years", type=float, required=True)
    lv.add_argument("--taken", type=int, default=0); lv.add_argument("--days-employed", type=int, default=365)
    sv = sub.add_parser("severance"); sv.add_argument("--rules", required=True)
    sv.add_argument("--start", required=True); sv.add_argument("--end", required=True)
    sv.add_argument("--monthly-avg", type=float, required=True); sv.add_argument("--route", default="N")
    sv.add_argument("--local-avg", type=float); sv.add_argument("--last-month", type=float)
    ck = sub.add_parser("clock"); ck.add_argument("--rules", required=True); ck.add_argument("--event", required=True)
    ck.add_argument("--today")
    sh = sub.add_parser("sheet"); sh.add_argument("case"); sh.add_argument("--rules", required=True)
    sh.add_argument("--today")
    a = p.parse_args(argv)
    rules = load_rules(a.rules)
    try:
        if a.cmd == "hours":
            with open(a.csv, newline="", encoding="utf-8") as f:
                res = overtime(list(csv.DictReader(f)), rules, a.monthly, a.paid)
        elif a.cmd == "leave":
            res = leave_payout(rules, a.monthly, a.career_years, a.taken, a.days_employed)
        elif a.cmd == "severance":
            res = severance(rules, d(a.start), d(a.end), a.monthly_avg, a.route, a.local_avg, a.last_month)
        elif a.cmd == "clock":
            res = clock(rules, d(a.event), d(a.today) if a.today else None)
        else:
            with open(a.case, encoding="utf-8") as f:
                case = json.load(f)
            verdict, md, _, _ = sheet(case, rules, d(a.today) if a.today else None)
            print(md)
            return 0 if verdict == "READY" else 1
    except RuleMissing as e:
        print("STOP: %s. Fill it from an official source first." % e, file=sys.stderr)
        return 2
    print(json.dumps(res, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
