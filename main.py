"""RecycleTrack command line program.

Arguments (all optional):
    (none)                         reads sample_log.txt
    LOGFILE                        reads that file
    LOGFILE START_DATE END_DATE    only reports dates in that range (YYYY-MM-DD)
"""
import sys

from log_parser import is_valid_date, read_log
from report import build_report, filter_by_date, save_report, summarize

DEFAULT_LOG = "sample_log.txt"
REPORT_FILE = "recycling_report.txt"


def main(args, report_path=REPORT_FILE):
    """Run the program with a list of arguments. Returns an exit code."""
    if len(args) not in (0, 1, 3):
        print("Usage: give no arguments, a LOGFILE, or a LOGFILE START_DATE END_DATE")
        return 2

    log_path = args[0] if args else DEFAULT_LOG
    start = None
    end = None
    if len(args) == 3:
        start, end = args[1].strip(), args[2].strip()
        if not (is_valid_date(start) and is_valid_date(end)):
            print("Error: dates must look like YYYY-MM-DD, for example 2025-03-01")
            return 2
        if start > end:
            print(f"Error: start date {start} is after end date {end}")
            return 2

    try:
        entries, warnings = read_log(log_path)
    except FileNotFoundError:
        print(f"Error: log file '{log_path}' was not found")
        return 1
    except UnicodeDecodeError:
        print(f"Error: log file '{log_path}' is not UTF-8 text (in VS Code use 'Save with Encoding' > UTF-8)")
        return 1
    except OSError as error:
        print(f"Error: cannot read log file '{log_path}': {error.strerror}")
        return 1

    for warning in warnings:
        print(warning)

    selected = filter_by_date(entries, start, end)
    text = build_report(summarize(selected), start, end, skipped=len(warnings))
    print(text, end="")
    try:
        save_report(text, report_path)
    except OSError as error:  # for example the file is open in Excel, or is a folder
        print(f"Error: could not save {report_path}: {error.strerror}")
        return 1
    print(f"Report saved to {report_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))