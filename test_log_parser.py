import os
import tempfile
import unittest

from log_parser import is_valid_date, parse_line, parse_lines, read_log


class TestIsValidDate(unittest.TestCase):
    def test_good_date(self):
        self.assertTrue(is_valid_date("2025-03-01"))

    def test_bad_dates(self):
        for text in ["2025/03/01", "25-03-01", "2025-3-1", "2025-13-01", "2025-03-32", "abcd-ef-gh", "",
                     "2025-+3-+5", "2025-0\u00b2-01"]:
            with self.subTest(text=text):
                self.assertFalse(is_valid_date(text))


class TestParseLine(unittest.TestCase):
    def test_example_from_task(self):
        entry = parse_line("2025-03-01,plastic,100,10")
        self.assertEqual(entry, {"date": "2025-03-01", "material": "plastic",
                                 "weight": 100.0, "contamination": 10.0})

    def test_spaces_and_capitals_are_cleaned(self):
        entry = parse_line(" 2025-03-01 , Plastic ,  50.5 , 2 ")
        self.assertEqual(entry["material"], "plastic")
        self.assertEqual(entry["weight"], 50.5)

    def test_missing_column(self):
        with self.assertRaises(ValueError) as ctx:
            parse_line("2025-03-01,plastic,100")
        self.assertIn("expected 4 columns but found 3", str(ctx.exception))

    def test_too_many_columns(self):
        with self.assertRaises(ValueError):
            parse_line("2025-03-01,plastic,100,10,extra")

    def test_non_numeric_weight(self):
        with self.assertRaises(ValueError) as ctx:
            parse_line("2025-03-01,plastic,lots,10")
        self.assertIn("not a number", str(ctx.exception))

    def test_nan_and_inf_are_rejected(self):
        for line in ["2025-03-01,plastic,nan,1", "2025-03-01,plastic,inf,1", "2025-03-01,plastic,100,NaN"]:
            with self.subTest(line=line):
                with self.assertRaises(ValueError) as ctx:
                    parse_line(line)
                self.assertIn("not a real number", str(ctx.exception))

    def test_bad_date(self):
        with self.assertRaises(ValueError) as ctx:
            parse_line("03/01/2025,plastic,100,10")
        self.assertIn("bad date", str(ctx.exception))

    def test_empty_material(self):
        with self.assertRaises(ValueError):
            parse_line("2025-03-01, ,100,10")

    def test_zero_weight(self):
        with self.assertRaises(ValueError):
            parse_line("2025-03-01,plastic,0,0")

    def test_negative_contamination(self):
        with self.assertRaises(ValueError):
            parse_line("2025-03-01,plastic,100,-1")

    def test_contamination_bigger_than_weight(self):
        with self.assertRaises(ValueError) as ctx:
            parse_line("2025-03-01,plastic,10,20")
        self.assertIn("larger than the total weight", str(ctx.exception))


class TestParseLines(unittest.TestCase):
    def test_bad_lines_warn_but_good_lines_survive(self):
        lines = [
            "date,material,weight_kg,contamination_kg\n",
            "2025-03-01,plastic,100,10\n",
            "2025-03-01,glass\n",
            "\n",
            "# a comment\n",
            "2025-03-02,glass,abc,1\n",
            "2025-03-02,paper,60,6\n",
        ]
        entries, warnings = parse_lines(lines)
        self.assertEqual([e["material"] for e in entries], ["plastic", "paper"])
        self.assertEqual(len(warnings), 2)
        self.assertTrue(warnings[0].startswith("WARNING line 3:"))
        self.assertTrue(warnings[1].startswith("WARNING line 6:"))

    def test_windows_line_endings(self):
        entries, warnings = parse_lines(["2025-03-01,plastic,100,10\r\n", "2025-03-01,metal,40,2\r\n"])
        self.assertEqual(warnings, [])
        self.assertEqual(entries[1]["contamination"], 2.0)


class TestReadLog(unittest.TestCase):
    def test_reads_file_with_bom_and_crlf(self):
        with tempfile.TemporaryDirectory() as folder:
            path = os.path.join(folder, "log.txt")
            with open(path, "wb") as f:
                f.write(b"\xef\xbb\xbf2025-03-01,plastic,100,10\r\n2025-03-02,glass,50,5\r\n")
            entries, warnings = read_log(path)
        self.assertEqual(warnings, [])
        self.assertEqual(entries[0]["date"], "2025-03-01")
        self.assertEqual(len(entries), 2)

    def test_missing_file_raises(self):
        with self.assertRaises(FileNotFoundError):
            read_log(os.path.join("no_such_folder", "missing.txt"))


if __name__ == "__main__":
    unittest.main()