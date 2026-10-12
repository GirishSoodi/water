import io
import os
import tempfile
import unittest
from contextlib import redirect_stdout

from main import main
from report import build_report, efficiency, filter_by_date, save_report, status_for, summarize


def make(date, material, weight, contamination):
    return {"date": date, "material": material, "weight": weight, "contamination": contamination}


ENTRIES = [
    make("2025-03-01", "plastic", 100.0, 10.0),
    make("2025-03-02", "plastic", 50.0, 5.0),
    make("2025-03-02", "paper", 60.0, 15.0),
    make("2025-03-05", "glass", 80.0, 4.0),
]


class TestEfficiency(unittest.TestCase):
    def test_task_example_is_90_percent(self):
        self.assertEqual(efficiency(100, 10), 90.0)

    def test_zero_weight_gives_zero(self):
        self.assertEqual(efficiency(0, 0), 0.0)

    def test_float_noise_is_rounded_away(self):
        # Unrounded this is 79.99999999999999, which would wrongly be flagged.
        eff = efficiency(1.9 + 3.8, 0.35 + 0.79)
        self.assertEqual(eff, 80.0)
        self.assertEqual(status_for(eff), "OK")

    def test_status_threshold(self):
        self.assertEqual(status_for(80.0), "OK")
        self.assertEqual(status_for(79.99), "Needs Improvement")


class TestFilterAndSummarize(unittest.TestCase):
    def test_filter_is_inclusive(self):
        kept = filter_by_date(ENTRIES, "2025-03-02", "2025-03-05")
        self.assertEqual(len(kept), 3)

    def test_filter_none_keeps_everything(self):
        self.assertEqual(len(filter_by_date(ENTRIES)), 4)

    def test_filter_outside_range_is_empty(self):
        self.assertEqual(filter_by_date(ENTRIES, "2026-01-01", "2026-12-31"), [])

    def test_summarize_groups_by_material(self):
        summary = summarize(ENTRIES)
        self.assertEqual(sorted(summary), ["glass", "paper", "plastic"])
        self.assertEqual(summary["plastic"]["weight"], 150.0)
        self.assertEqual(summary["plastic"]["contamination"], 15.0)
        self.assertEqual(summary["plastic"]["count"], 2)
        self.assertEqual(summary["plastic"]["efficiency"], 90.0)
        self.assertEqual(summary["paper"]["efficiency"], 75.0)


class TestBuildReport(unittest.TestCase):
    def test_report_flags_low_material(self):
        text = build_report(summarize(ENTRIES), skipped=1)
        self.assertIn("Date range: all dates", text)
        self.assertIn("Bad lines skipped: 1", text)
        paper_line = [line for line in text.splitlines() if line.startswith("Paper")][0]
        self.assertTrue(paper_line.endswith("Needs Improvement"))
        self.assertIn("Needs Improvement: Paper", text)

    def test_report_all_ok(self):
        text = build_report(summarize(ENTRIES[:2]), "2025-03-01", "2025-03-02")
        self.assertIn("Date range: 2025-03-01 to 2025-03-02", text)
        self.assertIn("All materials meet the 80% target.", text)

    def test_empty_report(self):
        text = build_report({}, "2026-01-01", "2026-01-31")
        self.assertIn("No entries found for this date range.", text)
        self.assertNotIn("All materials meet", text)

    def test_empty_log_without_range(self):
        text = build_report({})
        self.assertIn("No valid entries found in the log.", text)
        self.assertNotIn("date range", text.split("\n", 2)[2])

    def test_save_report_writes_file(self):
        with tempfile.TemporaryDirectory() as folder:
            path = os.path.join(folder, "out.txt")
            save_report("hello\n", path)
            with open(path, encoding="utf-8") as f:
                self.assertEqual(f.read(), "hello\n")


class TestMain(unittest.TestCase):
    def run_main(self, args, folder):
        buffer = io.StringIO()
        report_path = os.path.join(folder, "report_out.txt")
        with redirect_stdout(buffer):
            code = main(args, report_path)
        return code, buffer.getvalue(), report_path

    def test_full_run_writes_report_and_warns(self):
        with tempfile.TemporaryDirectory() as folder:
            log = os.path.join(folder, "log.txt")
            with open(log, "w", encoding="utf-8") as f:
                f.write("2025-03-01,plastic,100,10\n2025-03-01,paper,x,1\n2025-03-03,paper,60,15\n")
            code, out, report_path = self.run_main([log, "2025-03-01", "2025-03-02"], folder)
            self.assertEqual(code, 0)
            self.assertIn("WARNING line 2:", out)
            self.assertIn("Plastic", out)
            self.assertNotIn("Paper ", out)  # paper on 03-03 is outside the range
            with open(report_path, encoding="utf-8") as f:
                self.assertIn("Date range: 2025-03-01 to 2025-03-02", f.read())

    def test_missing_file(self):
        with tempfile.TemporaryDirectory() as folder:
            code, out, report_path = self.run_main([os.path.join(folder, "nope.txt")], folder)
            self.assertEqual(code, 1)
            self.assertIn("was not found", out)
            self.assertFalse(os.path.exists(report_path))

    def test_utf16_file_gives_clear_error(self):
        with tempfile.TemporaryDirectory() as folder:
            log = os.path.join(folder, "log.txt")
            with open(log, "w", encoding="utf-16") as f:
                f.write("2025-03-01,plastic,100,10\n")
            code, out, report_path = self.run_main([log], folder)
            self.assertEqual(code, 1)
            self.assertIn("is not UTF-8 text", out)
            self.assertFalse(os.path.exists(report_path))

    def test_folder_instead_of_file(self):
        with tempfile.TemporaryDirectory() as folder:
            code, out, _ = self.run_main([folder], folder)
            self.assertEqual(code, 1)
            self.assertIn("cannot read log file", out)

    def test_odd_digit_in_date_argument(self):
        with tempfile.TemporaryDirectory() as folder:
            code, out, _ = self.run_main(["log.txt", "2025-0\u00b2-01", "2025-03-05"], folder)
            self.assertEqual(code, 2)
            self.assertIn("YYYY-MM-DD", out)

    def test_report_cannot_be_saved(self):
        with tempfile.TemporaryDirectory() as folder:
            log = os.path.join(folder, "log.txt")
            with open(log, "w", encoding="utf-8") as f:
                f.write("2025-03-01,plastic,100,10\n")
            buffer = io.StringIO()
            with redirect_stdout(buffer):
                code = main([log], folder)  # a folder cannot be opened as a file
            self.assertEqual(code, 1)
            self.assertIn("Error: could not save", buffer.getvalue())
            self.assertNotIn("Report saved", buffer.getvalue())

    def test_bad_date_argument(self):
        with tempfile.TemporaryDirectory() as folder:
            code, out, _ = self.run_main(["log.txt", "2025-3-1", "2025-03-05"], folder)
            self.assertEqual(code, 2)
            self.assertIn("YYYY-MM-DD", out)

    def test_start_after_end(self):
        with tempfile.TemporaryDirectory() as folder:
            code, out, _ = self.run_main(["log.txt", "2025-03-05", "2025-03-01"], folder)
            self.assertEqual(code, 2)
            self.assertIn("is after end date", out)

    def test_wrong_argument_count(self):
        with tempfile.TemporaryDirectory() as folder:
            code, out, _ = self.run_main(["log.txt", "2025-03-05"], folder)
            self.assertEqual(code, 2)
            self.assertIn("Usage:", out)


if __name__ == "__main__":
    unittest.main()