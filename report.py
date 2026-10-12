"""Group log entries by material, compute efficiency and build the report text."""

THRESHOLD = 80.0


def filter_by_date(entries, start=None, end=None):
    """Keep entries whose date is between start and end (both inclusive)."""
    return [
        entry for entry in entries
        if (start is None or entry["date"] >= start)
        and (end is None or entry["date"] <= end)
    ]


def efficiency(weight, contamination):
    """Percentage of the weight that was clean, rounded to 2 decimals.

    Rounding stops float noise (79.99999999) from flagging a material
    that really sits exactly on the 80% line.
    """
    if weight <= 0:
        return 0.0
    return round((weight - contamination) / weight * 100, 2)


def summarize(entries):
    """Return {material: {"weight", "contamination", "efficiency", "count"}}."""
    totals = {}
    for entry in entries:
        material = entry["material"]
        if material not in totals:
            totals[material] = {"weight": 0.0, "contamination": 0.0, "count": 0}
        totals[material]["weight"] += entry["weight"]
        totals[material]["contamination"] += entry["contamination"]
        totals[material]["count"] += 1

    for material in totals:
        data = totals[material]
        data["efficiency"] = efficiency(data["weight"], data["contamination"])
    return totals


def status_for(eff):
    """'Needs Improvement' below the threshold, otherwise 'OK'."""
    if eff < THRESHOLD:
        return "Needs Improvement"
    return "OK"


def build_report(summary, start=None, end=None, skipped=0):
    """Build the report as one string, materials sorted alphabetically."""
    if start is None and end is None:
        range_text = "all dates"
    else:
        range_text = f"{start or 'beginning'} to {end or 'end'}"

    lines = [
        "RecycleTrack - Sorting Efficiency Report",
        f"Date range: {range_text}",
        f"Bad lines skipped: {skipped}",
        "-" * 64,
        f"{'Material':<12}{'Entries':>8}{'Total kg':>10}{'Contam kg':>11}{'Eff %':>8}  Status",
        "-" * 64,
    ]

    if not summary and range_text == "all dates":
        lines.append("No valid entries found in the log.")
    elif not summary:
        lines.append("No entries found for this date range.")
    for material in sorted(summary):
        data = summary[material]
        lines.append(
            f"{material.capitalize():<12}{data['count']:>8}{data['weight']:>10.1f}"
            f"{data['contamination']:>11.1f}{data['efficiency']:>8.1f}  {status_for(data['efficiency'])}"
        )

    lines.append("-" * 64)
    flagged = [m.capitalize() for m in sorted(summary) if status_for(summary[m]["efficiency"]) != "OK"]
    if flagged:
        lines.append("Needs Improvement: " + ", ".join(flagged))
    elif summary:
        lines.append("All materials meet the 80% target.")
    return "\n".join(lines) + "\n"


def save_report(text, path):
    """Write the report text to a file."""
    with open(path, "w", encoding="utf-8") as out:
        out.write(text)