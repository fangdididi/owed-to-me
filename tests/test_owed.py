import datetime as dt, json, os, sys, unittest
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "scripts"))
import owed

CN = owed.load_rules(os.path.join(HERE, "..", "rules", "cn.json"))
BLANK = owed.load_rules(os.path.join(HERE, "..", "rules", "blank.json"))


def row(date, s, e, brk=0, kind="work", comp="", ev="HARD"):
    return {"date": date, "start": s, "end": e, "break_min": brk, "day_type": kind, "comp_off": comp, "evidence": ev}


class Hours(unittest.TestCase):
    def test_weekday_extra_only(self):
        r = owed.overtime([row("2026-09-01", "09:00", "20:00", 60)], CN, 21750 * 8 / 8)
        self.assertEqual(r["hours"]["work"], 2.0)
        self.assertAlmostEqual(r["owed"], 2 * 125 * 1.5, places=2)  # 21750/21.75/8 = 125

    def test_rest_day_comp_off_cancels(self):
        r = owed.overtime([row("2026-09-06", "10:00", "15:00", kind="rest", comp="yes")], CN, 21750)
        self.assertEqual(r["owed"], 0)

    def test_rest_and_holiday_multipliers(self):
        r = owed.overtime([row("a", "10:00", "12:00", kind="rest"), row("b", "10:00", "12:00", kind="holiday")], CN, 21750)
        self.assertAlmostEqual(r["gross"], 2 * 125 * 2 + 2 * 125 * 3, places=2)

    def test_overnight_shift(self):
        self.assertEqual(owed.shift_hours("19:00", "01:00", 0), 6.0)

    def test_paid_already_and_grades(self):
        r = owed.overtime([row("a", "10:00", "12:00", kind="rest", ev="THIN")], CN, 21750, paid_already=100)
        self.assertEqual(r["by_grade"]["THIN"], 500.0)
        self.assertEqual(r["owed"], 400.0)

    def test_blank_pack_refuses(self):
        with self.assertRaises(owed.RuleMissing):
            owed.overtime([row("a", "09:00", "18:00")], BLANK, 10000)


class Leave(unittest.TestCase):
    def test_tiers_and_prorate(self):
        self.assertEqual(owed.leave_days_entitled(CN, 0.5, 365), 0)
        self.assertEqual(owed.leave_days_entitled(CN, 6, 365), 5)
        self.assertEqual(owed.leave_days_entitled(CN, 12, 365), 10)
        self.assertEqual(owed.leave_days_entitled(CN, 25, 365), 15)
        self.assertEqual(owed.leave_days_entitled(CN, 12, 200), 5)  # 10*200/365 = 5.48 -> 5

    def test_payout_extra_only(self):
        r = owed.leave_payout(CN, 21750, 6, 2, 365)
        self.assertEqual(r["unused"], 3)
        self.assertAlmostEqual(r["owed"], 3 * 1000 * 2.0, places=2)


class Severance(unittest.TestCase):
    def test_half_and_full_steps(self):
        a = owed.severance(CN, dt.date(2022, 3, 14), dt.date(2026, 10, 31), 12000)
        self.assertEqual(a["service_months"], 55)  # 4 y 7 m -> 5
        self.assertEqual(a["n"], 5.0)
        b = owed.severance(CN, dt.date(2024, 1, 1), dt.date(2025, 4, 1), 10000)
        self.assertEqual(b["n"], 1.5)

    def test_routes(self):
        s, e = dt.date(2020, 1, 1), dt.date(2023, 1, 1)
        self.assertEqual(owed.severance(CN, s, e, 10000, "N")["owed"], 30000)
        self.assertEqual(owed.severance(CN, s, e, 10000, "N+1", last_month=9000)["owed"], 39000)
        self.assertEqual(owed.severance(CN, s, e, 10000, "2N")["owed"], 60000)

    def test_high_earner_cap(self):
        r = owed.severance(CN, dt.date(2006, 1, 1), dt.date(2026, 1, 1), 50000, "N", local_avg=10000)
        self.assertTrue(r["capped"])
        self.assertEqual(r["n"], 12)
        self.assertEqual(r["owed"], 12 * 30000)


class Clock(unittest.TestCase):
    def test_states(self):
        ev = dt.date(2026, 1, 1)
        self.assertEqual(owed.clock(CN, ev, dt.date(2026, 3, 1))["state"], "OPEN")
        self.assertEqual(owed.clock(CN, ev, dt.date(2026, 12, 20))["state"], "URGENT")
        self.assertEqual(owed.clock(CN, ev, dt.date(2027, 1, 5))["state"], "EXPIRED")


class Sheet(unittest.TestCase):
    def case(self):
        with open(os.path.join(HERE, "..", "examples", "case.json"), encoding="utf-8") as f:
            return json.load(f)

    def test_example_flags_grade_and_risk(self):
        v, md, tiers, issues = owed.sheet(self.case(), CN, dt.date(2026, 11, 18))
        codes = {c for c, _ in issues}
        self.assertNotIn("L03", codes)  # M1 honestly says FIRM
        self.assertIn("L13", codes)     # chat evidence not secured
        self.assertEqual(v, "READY")
        self.assertAlmostEqual(tiers["SOLID"], 3310.34 + 60000 + 12000, places=2)
        self.assertAlmostEqual(tiers["LONGSHOT"], 827.59, places=2)

    def test_overclaimed_grade_and_2n_overlap(self):
        c = self.case()
        c["lines"][1]["grade"] = "HARD"
        c["lines"].append({"id": "M6", "type": "UNLAWFUL_2N", "amount": 120000, "formula": "2N",
                           "evidence": ["E6"], "event_date": "2026-10-31", "route": "ARBITRATE"})
        v, md, tiers, issues = owed.sheet(c, CN, dt.date(2026, 11, 18))
        codes = {cd for cd, _ in issues}
        self.assertIn("L03", codes)
        self.assertIn("L07", codes)
        self.assertEqual(v, "FIX")

    def test_missing_formula_blocks(self):
        c = self.case()
        del c["lines"][0]["formula"]
        v, *_ = owed.sheet(c, CN, dt.date(2026, 11, 18))
        self.assertEqual(v, "FIX")


if __name__ == "__main__":
    unittest.main()
