"""Read a recycling log file and turn each good line into an entry dictionary."""
import math


def is_valid_date(text):
    """Return True if text has the YYYY-MM-DD shape with month 01-12 and day 01-31.

    It does not know month lengths, so 2025-02-31 still passes.
    """
    parts = text.split("-")
    if len(parts) != 3:
        return False
    year, month, day = parts
    if len(year) != 4 or len(month) != 2 or len(day) != 2:
        return False
    if not (year.isdigit() and month.isdigit() and day.isdigit()):
        return False
    try:
        month_number = int(month)
        day_number = int(day)
        int(year)
    except ValueError:  # isdigit() also accepts characters like superscript 2 that int() rejects
        return False
    return 1 <= month_number <= 12 and 1 <= day_number <= 31


def parse_line(line):
    """Turn one 'date,material,weight_kg,contamination_kg' line into a dict.

    Raises ValueError with a readable message when the line is malformed.
    """
    fields = [field.strip() for field in line.split(",")]
    if len(fields) != 4:
        raise ValueError(f"expected 4 columns but found {len(fields)}")

    date, material, weight_text, contamination_text = fields
    if not is_valid_date(date):
        raise ValueError(f"bad date '{date}' (use YYYY-MM-DD)")
    if material == "":
        raise ValueError("material is empty")

    try:
        weight = float(weight_text)
        contamination = float(contamination_text)
    except ValueError:
        raise ValueError(f"weight '{weight_text}' or contamination '{contamination_text}' is not a number")
    # float() also accepts 'nan' and 'inf', which would poison the totals.
    if not (math.isfinite(weight) and math.isfinite(contamination)):
        raise ValueError(f"weight '{weight_text}' or contamination '{contamination_text}' is not a real number")

    if weight <= 0:
        raise ValueError("weight must be greater than 0")
    if contamination < 0:
        raise ValueError("contamination cannot be negative")
    if contamination > weight:
        raise ValueError("contamination is larger than the total weight")

    return {
        "date": date,
        "material": material.lower(),
        "weight": weight,
        "contamination": contamination,
    }


def parse_lines(lines):
    """Parse many lines. Returns (entries, warnings) and never stops on a bad line."""
    entries = []
    warnings = []
    for number, raw in enumerate(lines, start=1):
        line = raw.strip()
        if line == "" or line.startswith("#"):
            continue
        if line.lower().startswith("date,"):
            continue  # header row
        try:
            entries.append(parse_line(line))
        except ValueError as error:
            warnings.append(f"WARNING line {number}: {error} -> '{line}'")
    return entries, warnings


def read_log(path):
    """Read a log file from disk and parse it. Returns (entries, warnings)."""
    with open(path, "r", encoding="utf-8-sig") as log_file:
        lines = log_file.readlines()
    return parse_lines(lines)